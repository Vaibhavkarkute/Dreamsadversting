"use client";
import React from "react";

export default function PortalPage() {
  return (
    <main style={{ width: "100vw", height: "100vh", overflow: "hidden", margin: 0, padding: 0 }}>
      <iframe
        src="/owner-admin-portal.html"
        title="DreamsAdverstings — Master Owner & Staff Portal"
        style={{ width: "100%", height: "100%", border: "none", display: "block" }}
      />
    </main>
  );
}
