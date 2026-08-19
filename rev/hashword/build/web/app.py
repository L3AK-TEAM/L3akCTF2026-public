from flask import Flask, render_template, send_file

BINARY = "/srv/dist/hashword"

HINT_PATH = "/meow-meow-gimme-a-hint"

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/download")
def download():
    return send_file(BINARY, as_attachment=True, download_name="hashword")


@app.get(HINT_PATH)
def hints():
    return render_template("hints.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
