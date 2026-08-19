import MeowButton from "./meow-button";

const dependencies = `{
  "next": "16.0.6",
  "react": "19.2.0",
  "react-dom": "19.2.0",
  "@tailwindcss/postcss": "^4",
  "@types/node": "^20",
  "@types/react": "^19",
  "@types/react-dom": "^19",
  "eslint": "^9",
  "eslint-config-next": "16.0.6",
  "tailwindcss": "^4",
  "typescript": "^5"
}`;

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0a0a0a] text-[#00ff00] font-mono p-8">
      <div className="max-w-3xl mx-auto">
        <header className="mb-6 border-b border-[#00ff00]/30 pb-4">
          <h1 className="text-xl">$ ./vuln-check</h1>
        </header>

        <section className="mb-6 p-4 bg-[#111] border border-[#ff3333]/40 rounded">
          <p className="text-[#ff3333]">
            ⚠ This application is vulnerable to CVE-2025-55182.
          </p>
          <p className="text-[#ff3333]/70 mt-2 text-sm">
            Report platform protection bypasses via L3ak&apos;s CTF
            program.
          </p>
        </section>

        <section className="mb-6">
          <p className="text-[#00ff00]/50 text-sm mb-2">$ node --version</p>
          <pre className="bg-[#111] border border-[#00ff00]/20 rounded p-4 text-sm">
            <code>v22.23.0</code>
          </pre>
        </section>

        <section className="mb-6">
          <p className="text-[#00ff00]/50 text-sm mb-2">$ next --version</p>
          <pre className="bg-[#111] border border-[#00ff00]/20 rounded p-4 text-sm">
            <code>16.0.6</code>
          </pre>
        </section>

        <section className="mb-6">
          <p className="text-[#00ff00]/50 text-sm mb-2">
            $ cat package.json | jq .dependencies
          </p>
          <pre className="bg-[#111] border border-[#00ff00]/20 rounded p-4 text-sm">
            <code>{dependencies}</code>
          </pre>
        </section>

        <section className="mb-6 p-4 bg-[#111] border border-[#ffcc00]/40 rounded">
          <p className="text-[#ffcc00]">
            🚩 Submit the output of /readflag
          </p>
        </section>

        <section className="p-4 bg-[#111] border border-[#00ff00]/30 rounded">
          <p className="text-[#00ff00]/50 text-sm mb-2">$ ./meow</p>
          <MeowButton />
        </section>
      </div>
    </main>
  );
}