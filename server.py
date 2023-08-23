from flask import Flask, send_from_directory, Response
import os

app = Flask(__name__, static_folder='gw-client/dist')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        if path.endswith('.js'):
            with open(os.path.join(app.static_folder, path), 'r') as f:
                response = Response(f.read(), mimetype='application/javascript')
                return response
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run()
