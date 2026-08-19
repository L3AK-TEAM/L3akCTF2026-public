"use client";

import { useState } from "react";
import { meow } from "./actions";

export default function MeowButton() {
  const [result, setResult] = useState<string | null>(null);

  async function run() {
    setResult(await meow());
  }

  return (
    <>
      <button
        onClick={run}
        className="border border-[#00ff00]/50 text-[#00ff00] px-4 py-2 rounded text-sm hover:bg-[#00ff00]/10 transition-colors cursor-pointer"
      >
        Run Server Action
      </button>
      {result !== null && (
        <pre className="mt-4 bg-[#0a0a0a] border border-[#00ff00]/20 rounded p-4 text-sm">
          <code>{result}</code>
        </pre>
      )}
    </>
  );
}
