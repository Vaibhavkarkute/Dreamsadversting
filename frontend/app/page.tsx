"use client";

import React from "react";

export default function HomePage() {
  return (
    <main style={{ width: "100vw", height: "100vh", overflow: "hidden", margin: 0, padding: 0 }}>
      <iframe
        src="/interactive-marketplace.html"
        title="DreamsAdverstings Production OOH & DOOH Marketplace"
        style={{ width: "100%", height: "100%", border: "none", display: "block" }}
      />
    </main>
  );
}
