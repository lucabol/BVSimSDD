from . import create_app

app = create_app()

if __name__ == "__main__":
    # Allow overriding host/port/debug via environment variables for flexibility
    import os
    host = os.getenv("BVSIM_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("BVSIM_WEB_PORT", "8000"))
    debug_env = os.getenv("BVSIM_WEB_DEBUG", "true").lower()
    debug = debug_env in ("1", "true", "yes", "on")
    app.run(host=host, port=port, debug=debug)
