# import sys

# def list_video_sources() -> list[tuple[str,str]]:
#     """
#     Retorna lista de (value, label) para o dropdown:
#       - No Windows: usa pygrabber para pegar nome + índice
#       - Em Linux: /dev/video* + índice
#       - Sempre adiciona um placeholder RTSP
#     """
#     sources = []
#     # Windows: DirectShow
#     if sys.platform.startswith("win"):
#         try:
#             from pygrabber.dshow_graph import FilterGraph
#             graph = FilterGraph()
#             devs = graph.get_input_devices()  # lista de nomes
#             for idx, name in enumerate(devs):
#                 sources.append((str(idx), f"{name} (#{idx})"))
#         except Exception:
#             # fallback genérico
#             for i in range(5):
#                 sources.append((str(i), f"Camera {i}"))
#     else:
#         # Linux: enumerar /dev/video*
#         import glob, os
#         devs = sorted(glob.glob("/dev/video*"))
#         for dev in devs:
#             label = os.path.basename(dev)
#             sources.append((dev, f"{label}"))
#     # placeholder RTSP
#     sources.append(("rtsp://<IP-da-camera>:8080/video", "RTSP Stream"))
#     return sources
import sys

def list_video_sources() -> list[tuple[str, str]]:
    """
    Retorna lista de (value, label):
      - No Windows: obtém nome + índice via pygrabber
      - No Linux: lista /dev/video* + índice
      - Sempre inclui placeholder RTSP
    """
    sources: list[tuple[str,str]] = []

    if sys.platform.startswith("win"):
        try:
            from pygrabber.dshow_graph import FilterGraph
            graph = FilterGraph()
            devs = graph.get_input_devices()  # e.g. ["HD Pro Webcam C920", "OBS Virtual Camera"]
            for idx, name in enumerate(devs):
                sources.append((str(idx), f"{name} (#{idx})"))
        except Exception:
            # fallback genérico
            for i in range(5):
                sources.append((str(i), f"Câmera {i}"))
    else:
        import glob, os
        devs = sorted(glob.glob("/dev/video*"))
        for dev in devs:
            label = os.path.basename(dev)
            sources.append((dev, label))

    # placeholder RTSP
    sources.append(("rtsp://<IP-da-camera>:8080/video", "RTSP Stream"))
    return sources
