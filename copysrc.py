import os
import serial
import time
# まだ、エラーが多発、利用できるレベルではありません！！！
# Windowsのディレクトリを丸ごとシリアルに繋がったmicropyshonデバイスにREPLを使ってコピーする
def send_command(ser, command):
    # print(f"Sending command: {command}")
    ser.write((command + '\r\n').encode('utf-8'))
    time.sleep(0.1)
    response = ser.read_all().decode('utf-8')
    if "Traceback" in response:
        print(f"Error: {response}")
    return response

def copy_directory_to_device(directory, port, baudrate=115200):
    ser = serial.Serial(port, baudrate, timeout=1)
    time.sleep(2)  # Wait for the device to initialize

    for root, _, files in os.walk(directory):
        relative_path = os.path.relpath(root, directory)
        if relative_path != ".":
            print(f"Creating directory: {relative_path}")
            send_command(ser, f"import os; os.mkdir('{relative_path}')")
        
        for file in files:
            file_path = os.path.join(root, file)
            print(f"Copying file: {file_path} to {relative_path}/{file}")
            with open(file_path, 'rb') as f:
                content = f.read()
            
                target_path = os.path.join(relative_path, file).replace("\\", "/")
                send_command(ser, f"f = open('{target_path}', 'wb')")
                for i in range(0, len(content), 128):
                    chunk = content[i:i+128]
                    chunk_data = ",".join([str(b) for b in chunk])  # バイトデータを文字列に変換
                    send_command(ser, f"f.write(bytes([{chunk_data}]))")
                send_command(ser, "f.close()")
    
    ser.close()

def list_serial_ports():
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def select_serial_port():
    ports = list_serial_ports()
    if not ports:
        print("No serial ports found.")
        return None
    if len(ports) == 1:
        print(f"Only one serial port found: {ports[0]}")
        return ports[0]
    print("Available serial ports:")
    for i, port in enumerate(ports):
        print(f"{i + 1}: {port}")
    choice = int(input("Select a port by number: ")) - 1
    if 0 <= choice < len(ports):
        return ports[choice]
    else:
        print("Invalid selection.")
        return None

if __name__ == "__main__":
    # Example usage
    directory_to_copy = './src/'  # Change this to your desired directory
    selected_port = select_serial_port()
    if selected_port:
        print(f"Selected port: {selected_port}")
        copy_directory_to_device(directory_to_copy, selected_port)
    else:
        print("No valid port selected.")    
