def init_socketio_events(socketio):

    @socketio.on('connect')
    def handle_connect():
        print("Client connected")

    @socketio.on('disconnect')
    def handle_disconnect():
        print("Client disconnected")

    @socketio.on('send_message')
    def handle_send_message(data):
        # Broadcast the received message to all connected clients
        message = data.get('message')
        socketio.emit('receive_message', {'message': message})
