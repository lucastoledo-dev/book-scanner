import os
import json
from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, Response,
    render_template_string    # ← adicione isto
)
import cv2
from capture import CaptureThread
from pipeline import PipelineThread
from finalize import FinalizeThread
from video_sources import list_video_sources
import time

app = Flask(__name__)
SESSIONS_DIR = os.path.join(os.getcwd(), "data", "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Guarda as threads de cada sessão
threads: dict[str, tuple[CaptureThread, PipelineThread, FinalizeThread]] = {}

@app.route("/", methods=["GET"])
def dashboard():
    sessions = sorted(os.listdir(SESSIONS_DIR))
    sources  = list_video_sources()
    return render_template("dashboard.html",
                           sessions=sessions,
                           sources=sources)

@app.route("/new", methods=["POST"])
def new_session():
    name   = request.form.get("name", "").strip()
    source = request.form.get("video_source", "").strip()
    if not name or not source:
        return redirect(url_for("dashboard"))

    desc = request.form.get("description", "").strip()
    ocr  = bool(request.form.get("ocr"))

    base_slug = name.lower().replace(" ", "_")
    idx       = len([d for d in os.listdir(SESSIONS_DIR) if d.startswith(base_slug)]) + 1
    slug      = f"{base_slug}_{idx}"
    sess_path = os.path.join(SESSIONS_DIR, slug)

    # cria pastas raw/, processed/, final/
    for sub in ("raw", "processed", "final"):
        os.makedirs(os.path.join(sess_path, sub), exist_ok=True)

    # salva metadata
    meta = {"name": name, "description": desc, "source": source, "ocr": ocr}
    with open(os.path.join(sess_path, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # inicia threads
    cap  = CaptureThread(sess_path, source)
    pipe = PipelineThread(sess_path)
    fin  = FinalizeThread(sess_path)
    cap.start(); pipe.start(); fin.start()
    threads[slug] = (cap, pipe, fin)

    return redirect(url_for("view_session", slug=slug))

@app.route("/session/<slug>", methods=["GET"])
def view_session(slug):
    sess_path = os.path.join(SESSIONS_DIR, slug)
    if not os.path.isdir(sess_path):
        return redirect(url_for("dashboard"))

    # carrega meta.json para saber o source (value)
    meta = json.load(open(os.path.join(sess_path, "meta.json"), encoding="utf-8"))
    source = meta["source"]

    # descobre o label correspondente
    camera_label = source
    for value, label in list_video_sources():
        if value == source:
            camera_label = label
            break

    raw       = sorted(os.listdir(os.path.join(sess_path, "raw")))
    processed = sorted(os.listdir(os.path.join(sess_path, "processed")))

    return render_template("session.html",
                           slug=slug,
                           raw=raw,
                           processed=processed,
                           camera_label=camera_label)

@app.route("/video_feed/<slug>")
def video_feed(slug):
    """MJPEG do último frame com contorno marcado em VERMELHO."""
    if slug not in threads:
        return "Sessão não encontrada", 404
    cap_thread = threads[slug][0]

    def gen():
        while True:
            frame   = cap_thread.get_frame()
            contour = cap_thread.get_contour()
            if frame is None:
                time.sleep(0.1)
                continue

            # desenha contorno em vermelho
            if contour is not None:
                cv2.polylines(frame, [contour], True, (0,0,255), 2)

            ret, jpeg = cv2.imencode(".jpg", frame)
            if not ret:
                time.sleep(0.1)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                jpeg.tobytes() +
                b"\r\n"
            )

    return Response(gen(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/thumbs/<slug>")
def thumbs(slug):
    raw_dir = os.path.join(SESSIONS_DIR, slug, "raw")
    imgs = sorted(os.listdir(raw_dir))[-5:]
    tpl = """
    <div class="grid grid-cols-5 gap-2 mb-4">
      {% for img in imgs %}
        <img src="{{ url_for('serve_raw', slug=slug, filename=img) }}"
             alt="Página {{ img }}"
             class="border rounded-md">
      {% endfor %}
    </div>
    """
    return render_template_string(tpl, slug=slug, imgs=imgs)

@app.route("/sessions/<slug>/raw/<filename>")
def serve_raw(slug, filename):
    """
    Serve arquivos brutos (.jpg) da pasta raw/ de uma sessão.
    """
    raw_dir = os.path.join(SESSIONS_DIR, slug, "raw")
    return send_from_directory(raw_dir, filename)


@app.route("/finalize/<slug>", methods=["POST"])
def finalize(slug):
    if slug in threads:
        _, _, fin = threads[slug]
        fin.trigger_finalize()
    return redirect(url_for("download", slug=slug))

@app.route("/download/<slug>", methods=["GET"])
def download(slug):
    path = os.path.join(SESSIONS_DIR, slug, "final")
    return send_from_directory(path, "scan.pdf", as_attachment=True)

@app.route("/counts/<slug>")
def counts(slug):
    """
    Retorna um trecho de HTML com as contagens de raw/ e processed/ para HTMX.
    """
    sess_path = os.path.join(SESSIONS_DIR, slug)
    raw_dir       = os.path.join(sess_path, "raw")
    processed_dir = os.path.join(sess_path, "processed")

    raw_count       = len(os.listdir(raw_dir)) if os.path.isdir(raw_dir) else 0
    processed_count = len(os.listdir(processed_dir)) if os.path.isdir(processed_dir) else 0

    # devolve um snippet com grid de duas colunas
    return f"""
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div>Páginas capturadas:<br><strong>{raw_count}</strong></div>
      <div>Páginas processadas:<br><strong>{processed_count}</strong></div>
    </div>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
