from threading import Thread
import socket

# Configuration constants for various aspects of the server's operations.
config = {
    "IP": "bursasha",
    "PORT": 4321,

    "PROTOCOL_TAG": "\a\b",

    "TIMEOUT": 1,
    "TIMEOUT_RECHARGING": 5,

    "AUTH_KEYS": {
        0: [23019, 32037],
        1: [32037, 29295],
        2: [18789, 13603],
        3: [16443, 29533],
        4: [18189, 21952]
    },
    "MOD": 65536,

    "POSITION_TAG": "OK",

    "GIFT": [0,0]
}

# Data about sent and received packets, as well as their length.
packets = {
    "server": {
        "SERVER_MOVE": b"102 MOVE\a\b",
        "SERVER_TURN_LEFT": b"103 TURN LEFT\a\b",
        "SERVER_TURN_RIGHT": b"104 TURN RIGHT\a\b",
        "SERVER_PICK_UP": b"105 GET MESSAGE\a\b",
        "SERVER_LOGOUT": b"106 LOGOUT\a\b",
        "SERVER_KEY_REQUEST": b"107 KEY REQUEST\a\b",

        "SERVER_OK": b"200 OK\a\b",

        "SERVER_LOGIN_FAILED": b"300 LOGIN FAILED\a\b",
        "SERVER_SYNTAX_ERROR": b"301 SYNTAX ERROR\a\b",
        "SERVER_LOGIC_ERROR": b"302 LOGIC ERROR\a\b",
        "SERVER_KEY_OUT_OF_RANGE_ERROR": b"303 KEY OUT OF RANGE\a\b"
    },

    "robot": {
        "CLIENT_RECHARGING": "RECHARGING",
        "CLIENT_FULL_POWER": "FULL POWER"
    },

    "length": {
        "CLIENT_USERNAME": 20,
        "CLIENT_KEY_ID": 5,
        "CLIENT_CONFIRMATION": 7,
        "CLIENT_OK": 12,
        "CLIENT_RECHARGING": 12,
        "CLIENT_FULL_POWER": 12,
        "CLIENT_MESSAGE": 100
    }
}

# Messages for encountered exceptions that alert about the termination of a connection with a client-robot
# due to possible reasons outlined.
errors = {
    "TIMEOUT": "TIMEOUT ERROR!",
    "AUTH_KEYS": "AUTHENTICATION KEYS ERROR!",
    "LOGIN": "LOGIN ERROR!",
    "SYNTAX": "SYNTAX ERROR!",
    "LOGIC": "LOGIC ERROR!"
}

# Messages for the user interface of the program launched in the console.
ui = {
    "auth": [
        "- started authenticating.",
        "- sent username:",
        "- was requested to send auth key id.",
        "- sent auth key id:",
        "- was requested to confirm server hash:",
        "- sent robot hash to confirm:",
        "- authenticated successfully!"
    ],

    "search": [
        "- started finding gift.",
        "- moved right.",
        "- moved left.",
        "- moved forward:",
        "- picked up gift:",
        "- successfully logged out!"
    ],

    "connection": [
        "\t   === Created new connection ===",
        "\t     === Closed connection ==="
    ],

    "server": [
        f"    ### Server launched ###\n%%% IP: {config['IP']}, PORT: {config['PORT']} %%%",
        "    ### Server shut down ###"
    ],

    "recharge": "- +++ started recharging +++."
}

# All possible orientations in map space for each client-robot.
orientation = ["UP", "RIGHT", "DOWN", "LEFT"]


# Classes describing all possible exceptions that occur during the server's operations with clients.
class TimeoutException(Exception):
    def __init__(self): self.message = errors["TIMEOUT"]

class AuthKeysException(Exception):
    def __init__(self): self.message = errors["AUTH_KEYS"]

class LoginException(Exception):
    def __init__(self): self.message = errors["LOGIN"]

class LogicException(Exception):
    def __init__(self): self.message = errors["LOGIC"]

class SyntaxException(Exception):
    def __init__(self): self.message = errors["SYNTAX"]


# Class engine that implements the main functionality of any server - receiving data from the client
# and sending data back to the client. For the convenience of working with sockets, address,
# and client packets stream, 3 corresponding class variables are created.
class ServerEngine:
    def __init__(self, robot_socket, robot_address):
        self.robot_socket = robot_socket
        self.robot_address = robot_address
        self.robot_packets_queue = ""

    # This function implements the receiving of packets sent from the client. The main logic involves
    # an inner loop that uses the settimeout() function to determine the maximum time delay for receiving a packet.
    # If the delay exceeds the limit, the connection with the robot client is terminated. Otherwise, the received
    # packet part is placed in a "packet queue" (not exceeding the maximum length of the packet for that specific type),
    # and then, when possible, a complete packet
    # (containing PROTOCOL_TAG \a\b) will be retrieved from the queue and checked for allowable length.
    def _receive_packet(self, packet_length, timeout):
        packet_is_ready = config["PROTOCOL_TAG"] in self.robot_packets_queue
        packet_length = max(packet_length, packets["length"]["CLIENT_RECHARGING"])

        while True:
            if not packet_is_ready:
                try:
                    self.robot_socket.settimeout(timeout)
                    packet_buffer = self.robot_socket.recv(packet_length).decode()
                    self.robot_packets_queue += packet_buffer

                except socket.timeout: raise TimeoutException()

            packet_part = self.robot_packets_queue.find(config["PROTOCOL_TAG"])
            if packet_part == -1:
                if len(self.robot_packets_queue) > packet_length - len(config["PROTOCOL_TAG"]): raise SyntaxException()
                else: continue

            packet = self.robot_packets_queue[:packet_part + len(config["PROTOCOL_TAG"])]
            if not packet or len(packet) > packet_length: raise SyntaxException()

            self.robot_packets_queue = self.robot_packets_queue[packet_part + len(config["PROTOCOL_TAG"]):]

            return packet.replace(config["PROTOCOL_TAG"], "")

    # Function for convenient processing of the received packet for the presence of data on the client-robot's recharge
    # and the next mandatory received packet with data on the full robot charge, as well as checking
    # for a logical error in 2 possible places - without receiving a recharge packet and 5 seconds after receiving it.
    def process_packet(self, packet_length, timeout):
        processed_packet = self._receive_packet(packet_length, timeout)

        if processed_packet == packets["robot"]["CLIENT_FULL_POWER"]: raise LogicException()
        if processed_packet == packets["robot"]["CLIENT_RECHARGING"]:
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['recharge']}")
            processed_packet = \
                self._receive_packet(packets["length"]["CLIENT_FULL_POWER"], config["TIMEOUT_RECHARGING"])
            if processed_packet != packets["robot"]["CLIENT_FULL_POWER"]: raise LogicException()
            else: return self.process_packet(packet_length, timeout)

        return processed_packet

    # Function responsible for sending the ready packet to the client-robot.
    def send_packet(self, packet): self.robot_socket.send(packet)


# Class implementing the mechanism of client-robot authentication on the server. Inherits functionality from
# the engine class for working with client interactions. Corresponding class variables are created for
# ease of working with data received from the client
class AuthenticationMechanism(ServerEngine):
    def __init__(self, robot_socket, robot_address):
        super().__init__(robot_socket, robot_address)
        self.robot_username = self.robot_keyid = self.robot_base_hash = None

    # Function responsible for obtaining the client's username and subsequently processing it into a hash code.
    def _process_username(self):
        self.robot_username = self.process_packet(packets["length"]["CLIENT_USERNAME"], config["TIMEOUT"])

        username_converted = []
        for char in self.robot_username: username_converted.append(ord(char))
        self.robot_base_hash = (sum(username_converted) * 1000) % config["MOD"]
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['auth'][1]} {self.robot_username}.")

    # Function responsible for obtaining and processing the ID of the required key for authentication.
    def _process_keyid(self):
        self.send_packet(packets["server"]["SERVER_KEY_REQUEST"])
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['auth'][2]}")

        keyid = self.process_packet(packets["length"]["CLIENT_KEY_ID"], config["TIMEOUT"])
        if not keyid.isdigit(): raise SyntaxException()
        if int(keyid) < 0 or int(keyid) > 4: raise AuthKeysException()
        self.robot_keyid = int(keyid)
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['auth'][3]} {self.robot_keyid}.")

    # Function responsible for generating the server hash code for the corresponding client confirmation.
    def _process_server_hash(self):
        server_hash = (self.robot_base_hash + config["AUTH_KEYS"][self.robot_keyid][0]) % config["MOD"]
        self.send_packet((str(server_hash) + config["PROTOCOL_TAG"]).encode())
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['auth'][4]} {server_hash}.")

    # Function for the server to receive the client hash code and verify its validity.
    def _process_robot_hash(self):
        robot_hash = self.process_packet(packets["length"]["CLIENT_CONFIRMATION"], config["TIMEOUT"])
        if not robot_hash.isdigit() or len(robot_hash) > \
                packets["length"]["CLIENT_CONFIRMATION"] - len(config["PROTOCOL_TAG"]): raise SyntaxException()

        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['auth'][5]} {robot_hash}.")

        if (int(robot_hash) - config["AUTH_KEYS"][self.robot_keyid][1]) % config["MOD"] != self.robot_base_hash:
            raise LoginException()

    # Successful authentication completion.
    def _end_authentication(self):
        self.send_packet(packets["server"]["SERVER_OK"])
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['auth'][6]}")

    # Function returning unprocessed packets from the packets' queue.
    def get_robot_packets_queue(self): return self.robot_packets_queue

    # The entire authentication process.
    def authenticate_robot(self):
        print(f"\nRobot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['auth'][0]}")

        self._process_username()
        self._process_keyid()
        self._process_server_hash()
        self._process_robot_hash()
        self._end_authentication()


# Class implementing the mechanism of finding a secret message by the client-robot on the server map.
# Similar to the authentication mechanism class, inherits its functionality from the server engine class for
# interacting with the client's socket. For the convenience of the implementation of the mechanism,
# there are 2 variables for determining the current position and orientation of the robot on the map.
class SearchMechanism(ServerEngine):
    def __init__(self, robot_socket, robot_address):
        super().__init__(robot_socket, robot_address)
        self.robot_position = None
        self.robot_orientation = -1

    # Checking the validity of the robot's position coordinate.
    def _process_robot_coordinate(self, coordinate):
        return coordinate[1:].isdigit() if coordinate[0] == '-' else coordinate.isdigit()

    # Receiving and validating the current position of the client-robot.
    def _receive_robot_position(self):
        position_packet = self.process_packet(packets["length"]["CLIENT_OK"], config["TIMEOUT"]).split(' ')
        if len(position_packet) != 3 or position_packet[0] != config["POSITION_TAG"] \
            or not self._process_robot_coordinate(position_packet[1]) \
            or not self._process_robot_coordinate(position_packet[2]):
            raise SyntaxException()

        return [int(position_packet[1]), int(position_packet[2])]

    # Turning the client-robot to the right and changing its orientation depending on the actual orientation.
    def _move_robot_right(self):
        self.send_packet(packets["server"]["SERVER_TURN_RIGHT"])
        self.robot_position = self._receive_robot_position()
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][1]}")

        if self.robot_orientation != -1: self.robot_orientation = (self.robot_orientation + 1) % len(orientation)

    # Turning the client-robot to the left and changing its orientation depending on the actual orientation.
    def _move_robot_left(self):
        self.send_packet(packets["server"]["SERVER_TURN_LEFT"])
        self.robot_position = self._receive_robot_position()
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][2]}")

        if self.robot_orientation != -1: self.robot_orientation = (self.robot_orientation - 1) % len(orientation)

    # Moving the robot forward relative to the current position and orientation and describing
    # the case of collision with an obstacle: turning right, stepping forward, turning left, stepping forward.
    def _move_robot_forward(self):
        previous_robot_position = self.robot_position

        self.send_packet(packets["server"]["SERVER_MOVE"])
        new_robot_position = self._receive_robot_position()
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][3]} {new_robot_position}.")

        if self.robot_position == new_robot_position:
            self._move_robot_right()
            self.send_packet(packets["server"]["SERVER_MOVE"])
            new_robot_position = self._receive_robot_position()
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][3]} {new_robot_position}.")

            self._move_robot_left()
            previous_robot_position = self.robot_position
            self.send_packet(packets["server"]["SERVER_MOVE"])
            new_robot_position = self._receive_robot_position()
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][3]} {new_robot_position}.")

        self.robot_position = new_robot_position

        return previous_robot_position

    # Determining the first position of the robot relative to the 2 coordinates obtained after the first step forward.
    def _process_robot_initial_orientation(self, previous_robot_position):
        difference = [self.robot_position[0] - previous_robot_position[0],
                      self.robot_position[1] - previous_robot_position[1]]

        if difference[0] == -1 and difference[1] == 0: return orientation.index("LEFT")
        elif difference[0] == 1 and difference[1] == 0: return orientation.index("RIGHT")
        elif difference[0] == 0 and difference[1] == -1: return orientation.index("DOWN")
        else: return orientation.index("UP")

    # Choosing the orientation of the next robot step and changing the initial robot orientation for the next step.
    def _process_robot_next_move(self):
        difference = [config["GIFT"][0] - self.robot_position[0], config["GIFT"][1] - self.robot_position[1]]

        next_move_orientation = None
        if abs(difference[0]) > abs(difference[1]):
            if difference[0] > 0: next_move_orientation = orientation.index("RIGHT")
            elif difference[0] < 0: next_move_orientation = orientation.index("LEFT")
        else:
            if difference[1] > 0: next_move_orientation = orientation.index("UP")
            elif difference[1] < 0: next_move_orientation = orientation.index("DOWN")

        while self.robot_orientation != next_move_orientation:
            if self.robot_orientation < next_move_orientation: self._move_robot_right()
            else: self._move_robot_left()

    # Final stage of the client-robot on the server - receiving a secret message at coordinate [0,0]
    # and disconnection from the server.
    def _pick_up_gift_and_logout(self):
        self.send_packet(packets["server"]["SERVER_PICK_UP"])
        gift_message = self.process_packet(packets["length"]["CLIENT_MESSAGE"], config["TIMEOUT"])
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][4]} {gift_message}")

        self.send_packet(packets["server"]["SERVER_LOGOUT"])
        print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][5]}\n")

    # Setting the packet queue from the client after completing the authentication stage.
    def set_robot_packets_queue(self, robot_packets_queue): self.robot_packets_queue = robot_packets_queue

    # Function responsible for the entire process of finding the robot on the map. The main idea:
    # after the robot turns, the server receives the robot's coordinates without moving forward,
    # thus avoiding unnecessary steps from the defined step limit. Then the robot takes one step forward and
    # obtains new coordinates, after which the server knows the orientation of the robot and can direct it
    # towards the final gift. The internal loop describes all the necessary choices of direction and
    # movement of the robot. At the end, the final stage is performed.
    def launch_robot(self):
        print(f"\nRobot ({self.robot_address[0]}:{self.robot_address[1]}) {ui['search'][0]}")

        self._move_robot_right()
        previous_robot_position = self._move_robot_forward()
        self.robot_orientation = self._process_robot_initial_orientation(previous_robot_position)

        while self.robot_position != config["GIFT"]:
            self._process_robot_next_move()
            self._move_robot_forward()

        self._pick_up_gift_and_logout()


# Class responsible for all stages of interaction between the client-robot and the server.
class ConnectionMechanism:
    def __init__(self, robot_socket, robot_address):
        self.robot_socket = robot_socket
        self.robot_address = robot_address
        self.authentication_mechanism = AuthenticationMechanism(robot_socket, robot_address)
        self.search_mechanism = SearchMechanism(robot_socket, robot_address)

    # Here, all interactions are taking place: authentication mechanism launch, preparation for the gift search stage,
    # and the gift search stage itself. In case of any exceptions occurring at any stage,
    # they are caught in the try-catch block, and the client is disconnected from the server,
    # with the reason for the error displayed in the console.
    def create_connection(self):
        print(f"\n{ui['connection'][0]}")

        try:
            self.authentication_mechanism.authenticate_robot()
            self.search_mechanism.set_robot_packets_queue(self.authentication_mechanism.get_robot_packets_queue())
            self.search_mechanism.launch_robot()

        except TimeoutException as TE:
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) - {TE.message}\n")
        except AuthKeysException as AUE:
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) - {AUE.message}\n")
            self.authentication_mechanism.send_packet(packets["server"]["SERVER_KEY_OUT_OF_RANGE_ERROR"])
        except LoginException as LE:
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) - {LE.message}\n")
            self.authentication_mechanism.send_packet(packets["server"]["SERVER_LOGIN_FAILED"])
        except LogicException as LE:
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) - {LE.message}\n")
            self.search_mechanism.send_packet(packets["server"]["SERVER_LOGIC_ERROR"])
        except SyntaxException as SE:
            print(f"Robot ({self.robot_address[0]}:{self.robot_address[1]}) - {SE.message}\n")
            self.search_mechanism.send_packet(packets["server"]["SERVER_SYNTAX_ERROR"])

        self.robot_socket.close()
        print(f"{ui['connection'][1]}\n")


# Implementation of the server itself and its configuration.
class Server:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((config["IP"], config["PORT"]))
        self.server_socket.listen()

        print(f"\n\n{ui['server'][0]}\n")

    # Function responsible for connecting new clients. When a new robot client connects, a new thread
    # is created specifically to serve it. As the client has no impact on any server configuration data or variables,
    # there are no critical sections that need to be protected. Therefore, this approach of creating separate threads
    # to serve each specific client is a suitable and convenient implementation method.
    def launch(self):
        try:
            while True:
                new_robot_socket, new_robot_address = self.server_socket.accept()
                new_robot_connection = ConnectionMechanism(new_robot_socket, new_robot_address)
                new_robot_connection_thread = Thread(target=new_robot_connection.create_connection)
                new_robot_connection_thread.start()

        except KeyboardInterrupt: print(f"\n{ui['server'][1]}\n\n")
        self.server_socket.close()


if __name__ == '__main__':
    server = Server()
    server.launch()
