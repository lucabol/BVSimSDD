from . import create_app

app = create_app()

if __name__ == "__main__":
    # Simple dev server
    app.run(host="0.0.0.0", port=8000, debug=True)
