import os
import json
from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, Response
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

# @app.route("/video_feed/<slug>")
# def video_feed(slug):
#     """
#     Gera um stream MJPEG usando o último frame da CaptureThread.
#     """
#     if slug not in threads:
#         return "Sessão não encontrada", 404

#     cap_thread = threads[slug][0]

#     def gen():
#         while True:
#             frame = cap_thread.get_frame()
#             if frame is None:
#                 time.sleep(0.1)
#                 continue
#             ret, jpeg = cv2.imencode(".jpg", frame)
#             if not ret:
#                 time.sleep(0.1)
#                 continue
#             yield (b"--frame\r\n"
#                    b"Content-Type: image/jpeg\r\n\r\n" +
#                    jpeg.tobytes() + b"\r\n")

#     return Response(
#         gen(),
#         mimetype="multipart/x-mixed-replace; boundary=frame"
#     )

import time
import cv2
from flask import Response

@app.route("/video_feed/<slug>")
def video_feed(slug):
    """
    Stream MJPEG com overlay de contorno da página em verde.
    """
    if slug not in threads:
        return "Sessão não encontrada", 404

    cap_thread = threads[slug][0]

    def gen():
        while True:
            frame = cap_thread.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            # --- DETECÇÃO DO CONTORNO DA PÁGINA ---
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # binariza invertido para realçar bordas brancas do papel
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            cnts, _  = cv2.findContours(thresh,
                          cv2.RETR_EXTERNAL,
                          cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                # pega maior contorno (provável página)
                c = max(cnts, key=cv2.contourArea)
                # aproxima contorno para polígono
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                # desenha polilinha verde de espessura 2
                cv2.polylines(frame, [approx], True, (0,255,0), 2)

            # --- CODIFICAÇÃO E ENVIO DO FRAME ---
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

    return Response(
        gen(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/sessions/<slug>/raw/<filename>")
def serve_raw(slug, filename):
    path = os.path.join(SESSIONS_DIR, slug, "raw")
    return send_from_directory(path, filename)

@app.route("/sessions/<slug>/processed/<filename>")
def serve_processed(slug, filename):
    path = os.path.join(SESSIONS_DIR, slug, "processed")
    return send_from_directory(path, filename)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
