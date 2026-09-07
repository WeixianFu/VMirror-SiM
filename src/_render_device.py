"""Cycles device setup, shared by generated Blender scripts and unit tests."""


def configure_cycles_device(bpy, profile):
    """Select local hardware every time a blend is opened (no saved preferences).

    This function is injected into Blender subprocesses; keep imports local and
    do not depend on notebook-side packages or module globals.
    """
    import platform

    legacy = profile.get("apple_silicon", {})
    settings = profile.get("device")
    if settings is None:
        # Older exported/custom profiles remain usable.
        settings = {
            "backend": (legacy.get("compute_device_type", "METAL")
                        if legacy.get("enabled", False)
                        and legacy.get("cycles_device", "GPU") != "CPU"
                        else "CPU") if legacy else "AUTO",
            "use_metalrt": legacy.get("use_metalrt", True),
        }
    requested = str(settings.get("backend", "AUTO")).upper()
    if requested not in {"AUTO", "CPU", "METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"}:
        raise ValueError("Unknown device.backend: %r" % requested)

    system = platform.system()
    candidates = (["METAL"] if system == "Darwin" else
                  ["OPTIX", "CUDA", "HIP", "ONEAPI"])
    if requested != "AUTO":
        candidates = [] if requested == "CPU" else [requested]
    cy = bpy.context.scene.cycles
    # Never inherit GPU/denoising settings from another computer's blend.
    cy.device = "CPU"
    for attr in ("denoising_use_gpu", "preview_denoising_use_gpu"):
        if hasattr(cy, attr):
            setattr(cy, attr, False)

    result = {"requested_backend": requested, "backend": "CPU",
              "devices": [], "platform": system,
              "blender_version": bpy.app.version_string,
              "fallback_reason": None, "attempts": [], "warnings": []}
    prefs = None
    if candidates:
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
        except Exception as exc:
            result["attempts"].append({"backend": "GPU", "error": str(exc)})
    for backend in candidates if prefs is not None else []:
        try:
            prefs.compute_device_type = backend
            if hasattr(prefs, "refresh_devices"):
                prefs.refresh_devices()
            else:
                prefs.get_devices()
            selected = [d for d in prefs.devices if d.type == backend]
            for device in prefs.devices:
                device.use = device.type == backend
            if not selected:
                raise RuntimeError("No %s devices detected" % backend)
            cy.device = "GPU"
            result["backend"] = backend
            result["devices"] = [d.name for d in selected]
            break
        except Exception as exc:
            cy.device = "CPU"
            result["attempts"].append({"backend": backend, "error": str(exc)})

    if result["backend"] == "CPU" and candidates:
        if prefs is not None:
            for device in prefs.devices:
                device.use = device.type == "CPU"
        reason = "; ".join(item["backend"] + ": " + item["error"]
                           for item in result["attempts"])
        result["fallback_reason"] = reason
        if not settings.get("fallback_to_cpu", True):
            raise RuntimeError("No usable Cycles GPU: " + reason)
        print("[VMirror] GPU unavailable; using CPU. " + reason, flush=True)

    if result["backend"] == "METAL":
        try:
            enabled = settings.get("use_metalrt", True)
            if hasattr(prefs, "metalrt"):
                prefs.metalrt = "ON" if enabled else "OFF"
            elif hasattr(prefs, "use_metalrt"):
                prefs.use_metalrt = enabled
        except Exception as exc:
            result["warnings"].append("MetalRT: " + str(exc))

    use_gpu_denoising = (result["backend"] != "CPU"
                         and profile.get("cycles", {}).get("denoising_use_gpu", False))
    for attr in ("denoising_use_gpu", "preview_denoising_use_gpu"):
        if hasattr(cy, attr):
            setattr(cy, attr, use_gpu_denoising)
    result["denoising_use_gpu"] = bool(getattr(cy, "denoising_use_gpu", False))
    # Compatibility aliases for callers of the original Metal-only renderer.
    result["metal_devices"] = result["devices"] if result["backend"] == "METAL" else []
    result["apple_silicon_error"] = next(
        (a["error"] for a in result["attempts"] if a["backend"] == "METAL"), None)
    print("[VMirror] Cycles %s: %s" %
          (result["backend"], ", ".join(result["devices"]) or "CPU"), flush=True)
    return result
