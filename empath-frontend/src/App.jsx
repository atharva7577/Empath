import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./Home";
import Chat from "./Chat";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/chat" element={<Chat />} />
        {/* keep /app if you used it earlier */}
        <Route path="/app" element={<Chat />} />
      </Routes>
    </BrowserRouter>
  );
}
