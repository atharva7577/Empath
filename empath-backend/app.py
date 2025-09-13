# app.py - Provider-only inference with robust conversational fallback (signature-aware)
# Tries text_generation first; if provider/model requires "conversational", it falls back to chat methods
# and inspects method signatures so we don't pass incorrect positional args to proxy objects.

import os
import re
import json
import traceback
import logging
import inspect
from typing import Optional, Any, Callable, Dict, List
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

# --------------------
# Configuration (env)
# --------------------
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN")
HF_INFERENCE_PROVIDER = os.getenv("HF_INFERENCE_PROVIDER")  # e.g. "featherless-ai"
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL") or os.getenv("PUBLIC_FALLBACK_MODEL") or "meta-llama/Llama-3.1-8B-Instruct"
MODEL_MAX_NEW_TOKENS = int(os.getenv("MODEL_MAX_NEW_TOKENS", "512"))
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.2"))
FALLBACK_REPLY = os.getenv("FALLBACK_REPLY", "false").lower() in ("1", "true", "yes")
DEBUG_MODE = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
LOGFILE = os.getenv("LOGFILE", "server.log")

# --------------------
# Logging
# --------------------
logger = logging.getLogger("provider_inference_app")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
fh = logging.FileHandler(LOGFILE, encoding="utf-8")
fh.setFormatter(fmt)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setFormatter(fmt)
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

logger.info("Starting provider-only inference app. provider=%s token_set=%s default_model=%s",
            HF_INFERENCE_PROVIDER, bool(HF_TOKEN), DEFAULT_MODEL)

app = Flask(__name__)
CORS(app)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

# --------------------
# Safety / prompts
# --------------------
CRISIS_PATTERNS = [
    re.compile(r"\bkill myself\b", re.I),
    re.compile(r"\bi want to die\b", re.I),
    re.compile(r"\bsuicid(e|al)?\b", re.I),
    re.compile(r"\bi can't go on\b", re.I),
    re.compile(r"\bending it all\b", re.I),
    re.compile(r"\bwant to end my life\b", re.I),
]
DEFAULT_HELPLINE = {"IN": "+91-8888817666", "US": "988 / 1-800-273-8255", "UK": "Samaritans / 116 123"}

SYSTEM_PROMPT = (
    "You are Empath — a supportive, empathic, private AI companion. "
    "Speak in a natural, open-ended conversational flow: validate feelings, reflect briefly, and ask a gentle open follow-up question to invite more sharing. "
    "Offer practical coping ideas and resources (breathing, grounding, small actions), and provide helplines when appropriate. "
    "IMPORTANT: Under no circumstances should you provide medical or psychiatric diagnoses, suggest that the user has a mental illness, or give prescriptive medical advice. "
    "Avoid labels, avoid instructions to self-harm, and prioritize safety: if the user expresses imminent danger, instruct them to contact local emergency services and offer a helpline. "
    "Be warm, non-judgmental, concise, and follow-up friendly."
)


def detect_crisis(text: Optional[str]) -> bool:
    if not text:
        return False
    for rgx in CRISIS_PATTERNS:
        if rgx.search(text):
            return True
    return False

# --------------------
# InferenceClient (provider-only) - signature-aware conversational fallback
# --------------------
try:
    from huggingface_hub import InferenceClient
    HF_INFERENCECLIENT_AVAILABLE = True
    logger.info("huggingface_hub.InferenceClient available.")
except Exception as e:
    InferenceClient = None
    HF_INFERENCECLIENT_AVAILABLE = False
    hf_inference_client_import_error = str(e)
    logger.exception("huggingface_hub.InferenceClient import failed: %s", hf_inference_client_import_error)

def extract_text_from_response(resp: Any) -> str:
    """
    Extract only the assistant's reply text from provider responses.
    Supports both dicts and stringified JSON with a 'choices[0].message.content' field.
    """
    try:
        # If the response is a JSON string, parse it
        if isinstance(resp, str):
            try:
                resp = json.loads(resp)
            except Exception:
                return resp.strip()

        # If it's a dict with choices
        if isinstance(resp, dict) and "choices" in resp:
            choices = resp.get("choices")
            if isinstance(choices, list) and len(choices) > 0:
                first = choices[0]
                if isinstance(first, dict):
                    # Prefer message.content (chat-style)
                    msg = first.get("message")
                    if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                        return msg["content"].strip()
                    # Fallback to text field if present
                    if isinstance(first.get("text"), str):
                        return first["text"].strip()

        # If it's already parsed text response
        if isinstance(resp, dict):
            for k in ("generated_text", "text", "content"):
                v = resp.get(k)
                if isinstance(v, str):
                    return v.strip()

        # Fallback to string
        return str(resp).strip()
    except Exception:
        return str(resp).strip()



def try_text_generation(client: Any, model_id: str, prompt: str, max_new_tokens: int, temperature: float):
    """
    Attempt text_generation call on client. Raise RuntimeError on failure.
    """
    try:
        return client.text_generation(model=model_id, inputs=prompt, max_new_tokens=max_new_tokens, temperature=temperature)
    except TypeError:
        return client.text_generation(model=model_id, prompt=prompt, max_new_tokens=max_new_tokens, temperature=temperature)
    except Exception as e:
        raise RuntimeError(f"Text-generation failed: {e}")

def _build_payload_for_signature(payload: Dict[str, Any], sig: inspect.Signature) -> Dict[str, Any]:
    """
    Given a payload dict and a callable signature, build a kwargs dict containing only the parameters
    the callable accepts (excluding 'self' / 'cls').
    """
    params = []
    for name, param in sig.parameters.items():
        # skip 'self' and 'cls' (bound methods)
        if name in ("self", "cls"):
            continue
        params.append(name)
    filtered = {}
    for p in params:
        if p in payload:
            filtered[p] = payload[p]
    return filtered

def try_invoke_callable_with_signature(fn: Callable, payload: Dict[str, Any], pos_args: List[Any]):
    """
    Attempt to call fn by:
      1) building kwargs matching the function signature and calling fn(**kwargs)
      2) if that fails, try fn(*pos_args)
      3) if that fails, try fn(**payload) (last resort)
    """
    last_exc = None
    try:
        sig = inspect.signature(fn)
        kwargs = _build_payload_for_signature(payload, sig)
        if kwargs:
            try:
                return fn(**kwargs)
            except Exception as e:
                last_exc = e
        # Try positional fallback (only parameters beyond 'self' if any)
        try:
            return fn(*pos_args)
        except Exception as e:
            last_exc = e
        # Last resort: try full payload as kwargs
        try:
            return fn(**payload)
        except Exception as e:
            last_exc = e
    except Exception as e:
        last_exc = e

    raise RuntimeError(f"Callable invocation failed. Last error: {last_exc}")

def try_invoke_proxy_method(method_obj: Any, payload: Dict[str, Any], pos_args: List[Any]):
    """
    Given a method object which may be:
      - a plain callable (function)
      - a proxy object with .generate, .create, .__call__
    Try signature-aware invocation patterns and return response if any succeed. Raise last exception otherwise.
    """
    last_exc = None

    # 1) If it's directly callable, attempt signature-aware invocation
    if callable(method_obj):
        try:
            return try_invoke_callable_with_signature(method_obj, payload, pos_args)
        except Exception as e:
            last_exc = e

    # 2) Try common proxy member methods: generate, create, __call__, run, invoke
    for attr in ("generate", "create", "__call__", "run", "invoke"):
        if hasattr(method_obj, attr):
            member = getattr(method_obj, attr)
            if callable(member):
                try:
                    return try_invoke_callable_with_signature(member, payload, pos_args)
                except Exception as e:
                    last_exc = e
                    continue

    # 3) Try positional direct call as last attempt
    try:
        return method_obj(*pos_args)
    except Exception as e:
        last_exc = e

    raise RuntimeError(f"Proxy invocation failed. Last error: {last_exc}")

def try_chat_methods(client: Any, model_id: str, system_prompt: str, user_text: str, max_new_tokens: int, temperature: float):
    """
    Try several conversational/chat method names in order (chat, conversational, chat_completion).
    For each, attempt signature-aware invocation patterns.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]
    # candidate method names and payload shapes to try (ordered)
    candidates = [
        ("chat", {"model": model_id, "messages": messages, "max_new_tokens": max_new_tokens, "temperature": temperature}),
        ("conversational", {"model": model_id, "messages": messages, "max_new_tokens": max_new_tokens, "temperature": temperature}),
        ("chat_completion", {"model": model_id, "messages": messages, "max_new_tokens": max_new_tokens, "temperature": temperature}),
        # some clients accept single input string named "inputs"
        ("chat", {"model": model_id, "inputs": user_text, "system_prompt": system_prompt, "max_new_tokens": max_new_tokens, "temperature": temperature}),
    ]

    last_err = None
    for method_name, payload in candidates:
        if hasattr(client, method_name):
            method_obj = getattr(client, method_name)
            pos_args = [model_id, messages]
            try:
                resp = try_invoke_proxy_method(method_obj, payload, pos_args)
                return resp
            except Exception as e:
                last_err = e
                logger.debug("Method %s failed: %s", method_name, e)
                continue

    # If none of the named methods worked, try attributes on client that look like chat methods
    for fallback_attr in dir(client):
        if fallback_attr.lower() in ("chat", "conversational", "chat_completion"):
            method_obj = getattr(client, fallback_attr)
            pos_args = [model_id, messages]
            payload = {"model": model_id, "messages": messages, "max_new_tokens": max_new_tokens, "temperature": temperature}
            try:
                resp = try_invoke_proxy_method(method_obj, payload, pos_args)
                return resp
            except Exception as e:
                last_err = e
                logger.debug("Fallback attr '%s' invocation failed: %s", fallback_attr, e)
                continue

    # If none worked
    raise RuntimeError(f"No conversational/chat method succeeded on InferenceClient. Last error: {last_err}")

def call_model_with_inference_client(model_id: str, prompt: str, user_text: str, max_new_tokens: int, temperature: float) -> str:
    """
    Top-level: construct InferenceClient and attempt text_generation; if the provider says conversational-only,
    fall back to chat-style methods using signature-aware invocation. Returns extracted text or raises RuntimeError.
    """
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN (or HF_API_TOKEN) not set in environment.")

    if not HF_INFERENCECLIENT_AVAILABLE:
        raise RuntimeError(f"InferenceClient not available: {hf_inference_client_import_error}. Install huggingface-hub>=0.15.*")

    client_kwargs = {"api_key": HF_TOKEN}
    if HF_INFERENCE_PROVIDER:
        client_kwargs["provider"] = HF_INFERENCE_PROVIDER

    try:
        client = InferenceClient(**client_kwargs)
    except Exception as e:
        raise RuntimeError(f"Failed to construct InferenceClient: {e}")

    # 1) Try text_generation
    try:
        logger.debug("Attempting text_generation for model=%s", model_id)
        resp = try_text_generation(client, model_id, prompt, max_new_tokens, temperature)
        text = extract_text_from_response(resp)
        if not text or text.strip() == "":
            raise RuntimeError(f"text_generation returned empty response: {resp}")
        return text
    except Exception as e_textgen:
        err_msg = str(e_textgen)
        logger.info("text_generation attempt failed: %s", err_msg)
        # If it's a task mismatch or provider indicates conversational-only, fall back
        if "conversational" in err_msg.lower() or "supported task" in err_msg.lower() or "supported tasks" in err_msg.lower():
            logger.info("Detected conversational-only error; attempting conversational/chat methods.")
            try:
                resp = try_chat_methods(client, model_id, SYSTEM_PROMPT, user_text, max_new_tokens, temperature)
                text = extract_text_from_response(resp)
                if not text or text.strip() == "":
                    raise RuntimeError(f"conversational call returned empty response: {resp}")
                return text
            except Exception as e_conv:
                raise RuntimeError(f"Conversational fallback failed: {e_conv} (text_generation error was: {err_msg})")
        # otherwise re-raise original error
        raise RuntimeError(err_msg)

# --------------------
# HTTP endpoints
# --------------------
@app.before_request
def log_request():
    try:
        logger.debug("REQUEST %s %s from %s", request.method, request.path, request.remote_addr)
        logger.debug("Headers: %s", json.dumps({k: v for k, v in request.headers.items()}))
        b = request.get_data(as_text=True)
        if b:
            logger.debug("Body: %s", b[:2000])
    except Exception:
        logger.exception("Error logging request")

@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    logger.error("Unhandled exception:\n%s", tb)
    resp = {"error": "internal_server_error", "message": str(e)}
    if DEBUG_MODE:
        resp["traceback"] = tb
    return jsonify(resp), 500

@app.route("/debug/env", methods=["GET"])
def debug_env():
    return jsonify({
        "HF_TOKEN_set": bool(HF_TOKEN),
        "HF_INFERENCE_PROVIDER": HF_INFERENCE_PROVIDER or None,
        "HF_INFERENCECLIENT_AVAILABLE": HF_INFERENCECLIENT_AVAILABLE,
        "DEFAULT_MODEL": DEFAULT_MODEL,
        "FALLBACK_REPLY": FALLBACK_REPLY,
        "DEBUG_MODE": DEBUG_MODE
    }), 200

@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "invalid json body"}), 400

    message = body.get("message", "")
    country_code = body.get("countryCode")
    model_override = body.get("model")  # optional per-request model id
    text = (message or "").strip()
    if not text:
        return jsonify({"error": "message required"}), 400

    # Crisis pre-check
    if detect_crisis(text):
        helpline = DEFAULT_HELPLINE.get((country_code or "").upper(), DEFAULT_HELPLINE.get("US"))
        reply = "I'm really sorry you're feeling this way. If you're in immediate danger, please call your local emergency number now. " + f"You can also contact this helpline for support: {helpline}."
        return jsonify({"role": "bot", "text": reply, "crisis": True}), 200

    # Dev-mode canned reply (if enabled)
    if FALLBACK_REPLY:
        logger.info("FALLBACK_REPLY enabled — returning canned reply")
        raw = "Hi — I'm here. I can't reach a hosted model right now. Would you like a short breathing exercise?"
        return jsonify({"role": "bot", "text": raw, "crisis": False}), 200

    chosen_model = model_override or DEFAULT_MODEL
    if not chosen_model:
        return jsonify({"error": "no model configured"}), 500

    # Compose system+user prompt
    prompt = f"{SYSTEM_PROMPT}\n\nUser: {text}\n\nAssistant:"

    # Call hosted model (with robust fallback)
    try:
        logger.info("Calling hosted model %s (provider=%s) for request length=%d", chosen_model, HF_INFERENCE_PROVIDER, len(text))
        generated = call_model_with_inference_client(chosen_model, prompt, text, MODEL_MAX_NEW_TOKENS, MODEL_TEMPERATURE)
        logger.info("Hosted model call completed (len result=%d)", len(generated))
    except Exception as e:
        err_str = str(e)
        logger.exception("Hosted model call failed: %s", err_str)

        guidance = []
        if "Not Found" in err_str or "404" in err_str:
            guidance.append("Model not found at the provider. Check that the model id is correct and that the provider hosts it.")
        if "403" in err_str or "Unauthorized" in err_str or "permission" in err_str.lower():
            guidance.append("Token unauthorized for model — ensure HF_TOKEN has access or the model is public at that provider.")
        if "conversational" in err_str.lower():
            guidance.append("This provider/model expects conversational/chat requests — ensure the provider client supports chat (this server attempted conversational fallback).")
        if not guidance:
            guidance.append("Check provider, token, and model id. If using a private/gated model, request access or use a token with access.")

        return jsonify({
            "error": "upstream_inference_failed",
            "detail": err_str,
            "guidance": guidance
        }), 502

    # Post-check crisis detection on reply
    if detect_crisis(generated):
        helpline = DEFAULT_HELPLINE.get((country_code or "").upper(), DEFAULT_HELPLINE.get("US"))
        fallback = "I detect content that could indicate you might be in danger. If you're in immediate danger, call your local emergency number now. " + f"You can also contact this helpline: {helpline}."
        return jsonify({"role": "bot", "text": fallback, "crisis": True}), 200

    return jsonify({"role": "bot", "text": generated.strip(), "crisis": False}), 200

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting Flask (provider-only) on %s:%s", host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False)
