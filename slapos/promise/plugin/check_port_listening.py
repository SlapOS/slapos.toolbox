from .check_socket_listening import RunPromise as SocketPromise

class RunPromise(SocketPromise):
  def __init__(self, config):
    config['host'] = config.pop('hostname')
    super(RunPromise, self).__init__(config)
