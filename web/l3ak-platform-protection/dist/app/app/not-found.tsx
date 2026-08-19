import Link from "next/link";

const response = `HTTP/1.1 404 Not Found
Content-Type: text/html

{
  "error": "Not Found",
  "message": "Oops! The page you're looking for doesn't exist.",
  "statusCode": 404
}`;

export default function NotFound() {
  return (
    <main className="min-h-screen bg-[#0a0a0a] text-[#ff3333] font-mono p-8">
      <div className="max-w-3xl mx-auto">
        <header className="mb-8 border-b border-[#ff3333]/30 pb-4">
          <h1 className="text-xl">$ curl -I /unknown</h1>
        </header>

        <pre className="bg-[#111] border border-[#ff3333]/20 rounded p-6 overflow-x-auto text-sm leading-relaxed">
          <code>{response}</code>
        </pre>

        <footer className="mt-8">
          <Link href="/" className="text-[#00ff00] hover:underline">
            → cd /
          </Link>
        </footer>
      </div>
    </main>
  );
}
