# **Multithreaded Python TCP Robot Server** 🤖

## **Repository Overview** 📄
This repository contains a _multithreaded_ **TCP** server implementation designed to control remote robots, 
allowing them to authenticate, navigate to a target coordinate, and retrieve a secret message. 
The project is implemented in **Python** and adheres to the specifications provided by the university **Computer Networks** course.

## **Repository Structure** 📂
- **`main.py`**: The main server program implementing the multithreaded TCP server.
- **`README.md`**: This README file providing an overview and usage instructions.
- **`tester-arm`**: The tester executable for ARM architecture to validate the server implementation against predefined tests.

## **Course Description and Task Overview** 📚
The **Computer Networks** course includes practical and theoretical tasks focusing on network communication protocols. 
The specific task is to create a _multithreaded_ server for **TCP/IP** communication that can handle multiple clients (robots) simultaneously. 
Each robot starts at a random coordinate and must navigate to the origin **[0,0]** to pick up a secret message.

### **Detailed Specification** 🔍

#### **Communication Protocol** 🔐
Communication between the server and robots is conducted via a pure textual protocol with commands ending in a special sequence **`"\a\b"`**.

#### **Server Messages** 📩
- `SERVER_MOVE`: Command to move one position forward.
- `SERVER_TURN_LEFT`: Command to turn left.
- `SERVER_TURN_RIGHT`: Command to turn right.
- `SERVER_PICK_UP`: Command to pick up the message.
- `SERVER_LOGOUT`: Command to terminate the connection after a successful message discovery.
- `SERVER_KEY_REQUEST`: Command to request Key ID for authentication.
- `SERVER_OK`: Positive acknowledgment.
- `SERVER_LOGIN_FAILED`: Authentication failed.
- `SERVER_SYNTAX_ERROR`: Incorrect message syntax.
- `SERVER_LOGIC_ERROR`: Message sent in an incorrect situation.
- `SERVER_KEY_OUT_OF_RANGE_ERROR`: Key ID out of the expected range.

#### **Client Messages** 📨
- `CLIENT_USERNAME`: Message with the username.
- `CLIENT_KEY_ID`: Message with the Key ID.
- `CLIENT_CONFIRMATION`: Message with the confirmation code.
- `CLIENT_OK`: Confirmation of performed movement, including robot coordinates.
- `CLIENT_RECHARGING`: Robot starts recharging.
- `CLIENT_FULL_POWER`: Robot has recharged and resumes operations.
- `CLIENT_MESSAGE`: Text of the discovered secret message.

#### **Authentication Process** 🔒
1. **Client sends username.**
2. **Server requests Key ID.**
3. **Client sends Key ID.**
4. **Server sends a confirmation code calculated using the username and server key.**
5. **Client sends its confirmation code.**
6. **Server verifies the confirmation code and responds with `SERVER_OK` or `SERVER_LOGIN_FAILED`.**

#### **Robot Navigation** 📡
The server guides the robot to the origin **[0,0]** using a series of `SERVER_MOVE`, `SERVER_TURN_LEFT`, and `SERVER_TURN_RIGHT` commands. 
The robot responds with its current coordinates after each move.

#### **Secret Message Discovery** 🎁
Once at **[0,0]**, the server sends `SERVER_PICK_UP` to retrieve the secret message from the robot. 
The server then sends `SERVER_LOGOUT` to terminate the connection.

#### **Recharging Process** 🔋
Robots notify the server when they start recharging (`CLIENT_RECHARGING`) and resume operations with `CLIENT_FULL_POWER`.

### **Special Situations and Error Handling** ⛔️
- **Timeouts**: Connections are terminated if messages are not received within specified intervals.
- **Syntax Errors**: The server responds with `SERVER_SYNTAX_ERROR` for incorrect message formats.
- **Logic Errors**: Errors during the recharging process result in `SERVER_LOGIC_ERROR`.

## **Technologies and Concepts Used** 🛠️
- **Python**:
    - _Multithreading_ with the `Thread` class from the `threading` module.
    - _Socket programming_ using the `socket` module.
    - Exception handling for robust error detection and response.
- **TCP/IP Communication**:
    - Implementing a _custom communication protocol_ over TCP.
    - Managing _concurrent client connections_ using threads.

## **Launching the Server and Client** 🚀

### **Running the Server**
1. **Ensure Python is installed on your system.**
2. **Navigate to the project directory.**
3. **Run the server using the following command:**
```sh
python3 main.py
```

### **Running the Tester**
1. **Ensure the tester executable is available in the project directory.**
2. **Launch the tester in a compatible environment (e.g., VirtualBox with Tiny Core Linux).**
3. **Run the tester with the appropriate parameters:**
   ```sh
   tester <port number> <server address> [test number(s)]
   ```
    - Example:
      ```sh
      tester 4321 127.0.0.1 2 3 8 | less
      ```

## **Conclusion** 📝
This repository provides a comprehensive implementation of a _multithreaded_ **TCP** server for robot control, following the detailed specifications provided by the **Computer Networks** course. 
The project demonstrates practical applications of network programming, multithreading, and custom protocol implementation in Python.