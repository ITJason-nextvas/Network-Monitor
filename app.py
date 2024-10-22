import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import psutil
import socket
import requests
import speedtest
import time
import datetime
import subprocess
import csv
import threading
import tabulate
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from requests.exceptions import RequestException

# Function to get the local IP address (private IP)
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error retrieving local IP: {e}")
        return None

# Function to get the public IP address (external IP)
def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org")
        response.raise_for_status()
        public_ip = response.text
        print(public_ip)
        return public_ip
    except RequestException as e:
        print(f"Error retrieving public IP: {e}")
        return None
    
def get_isp_info(ip):
    # First API: ipinfo.io
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        response.raise_for_status()
        data = response.json()
        isp = data.get('org', None)  # 'org' field contains ISP information
        if isp:
            print(f"API call succesful! ISP: {isp}")
            return isp
    except RequestException:
        print("ipinfo.io failed, trying the next API...")

    # Second API: ipapi.co
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json")
        response.raise_for_status()
        data = response.json()
        isp = data.get('org', None)
        if isp:
            print(f"API call succesful! ISP: {isp}")
            return isp
    except RequestException:
        print("ipapi.co failed, trying the next API...")

    # Third API: ip-api.com
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}")
        response.raise_for_status()
        data = response.json()
        isp = data.get('org', None)
        if isp:
            print(f"API call succesful! ISP: {isp}")
            return isp
    except RequestException:
        print("ip-api.com failed.")

    # If all APIs fail, return a default value
    return "N/A"


# Function to get internet speed (download and upload speeds)
def get_internet_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()  # Get the best server for testing
        download_speed = st.download() / 1_000_000  # Convert from bps to Mbps
        upload_speed = st.upload() / 1_000_000  # Convert from bps to Mbps
        return download_speed, upload_speed
    except Exception as e:
        print(f"Error retrieving internet speed: {e}")
        return None, None

# Function to get network info (local IPs)
def get_network_info():
    net_info = psutil.net_if_addrs()
    ip_addresses = []
    for interface, addrs in net_info.items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip_addresses.append((interface, addr.address))
    return ip_addresses

# Email sending function
def send_email(subject, body, recipient_email, attached_file=None):
    sender_email = "nextvasnetworkmonitor@gmail.com"
    sender_password = "Nextvas@123"

    # Set up the MIME
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Body and attachments
    msg.attach(MIMEText(body, 'plain'))

    # Attach file if provided
    if attached_file:
        with open(attached_file, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(attached_file)}')
            msg.attach(part)

    try:
        # Set up the server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)

        # Convert the message to a string and send
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()
        

# Add theme and font customization to the NetworkMonitorApp
class NetworkMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Monitor Nextvas")

        self.public_ip = get_public_ip()  # Get public IP address
        self.isp_info = get_isp_info(self.public_ip)  # Get local IP address
        self.is_connected = self.public_ip is not None  # Check if there's an internet connection
        self.history_tree = None
        
        # Variables for theme and font size
        self.theme = tk.StringVar(value="Light")
        self.font_size = tk.IntVar(value=16)

        # Create labels to display IP, speed, and connection status
        self.label_ip = tk.Label(root, text="IP Address: N/A", font=("Helvetica", self.font_size.get()))
        self.label_ip.pack(pady=10)

        self.label_isp = tk.Label(root, text="ISP: N/A", font=("Helvetica", self.font_size.get()))
        self.label_isp.pack(pady=10)

        self.label_status = tk.Label(root, text="Internet: Disconnected", font=("Helvetica", self.font_size.get()))
        self.label_status.pack(pady=10)

        self.label_netinfo = tk.Label(root, text="Network Info: N/A", font=("Helvetica", 12))
        self.label_netinfo.pack(pady=10)

        self.label_speed = tk.Label(root, text="Speed: N/A", font=("Helvetica", self.font_size.get()))
        self.label_speed.pack(pady=10)

        # Create a settings menu for dark mode and font size
        menubar = tk.Menu(root)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Toggle Dark Mode", command=self.toggle_dark_mode)
        settings_menu.add_command(label="Change Font Size", command=self.change_font_size)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        # Add Export button
        export_menu = tk.Menu(menubar, tearoff=0)
        export_menu.add_command(label="Export to CSV", command=self.export_to_csv)
        menubar.add_cascade(label="Export", menu=export_menu)

        root.config(menu=menubar)

        # Remaining initialization (refresh button, progress bar, etc.) goes here...
        self.refresh_button = tk.Button(root, text="Refresh Network Info", command=self.run_fake_refresh, font=("Helvetica", 12))
        self.refresh_button.pack(pady=10)

        self.speed_button = tk.Button(root, text="Test Internet Speed", command=self.run_fake_speed_test, font=("Helvetica", 12))
        self.speed_button.pack(pady=10)

        # History of network data
        self.network_history = []

        # Add a button to open the history window
        self.history_button = tk.Button(root, text="View History", command=self.open_history_window, font=("Helvetica", 12))
        self.history_button.pack(pady=10)

        # # Add an "Export" button to save the history to a CSV file
        # self.export_button = tk.Button(root, text="Export History", command=self.export_history_to_csv)
        # self.export_button.pack(pady=10)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)

        # Label and entry for the user to enter the ping address
        self.ping_label = tk.Label(root, text="Enter address to ping:", font=("Helvetica", 12))
        self.ping_label.pack(pady=10)

        self.ping_entry = tk.Entry(root, font=("Helvetica", 12))
        self.ping_entry.pack(pady=10)

        # Button to open the ping window
        self.ping_button = tk.Button(root, text="Ping", command=self.open_ping_window, font=("Helvetica", 12))
        self.ping_button.pack(pady=10)

        self.monitor_network_changes()

    def toggle_dark_mode(self):
        if self.theme.get() == "Light":
            self.apply_theme("black", "#F5F5DC")  # Cream white text
            self.theme.set("Dark")
        else:
            self.apply_theme("white", "black")
            self.theme.set("Light")

    def apply_theme(self, bg_color, fg_color):
        self.root.config(bg=bg_color)
        self.label_ip.config(bg=bg_color, fg=fg_color)
        self.label_isp.config(bg=bg_color, fg=fg_color)
        self.label_status.config(bg=bg_color, fg=fg_color)
        self.label_netinfo.config(bg=bg_color, fg=fg_color)
        self.label_speed.config(bg=bg_color, fg=fg_color)
        self.refresh_button.config(bg=bg_color, fg=fg_color)
        self.speed_button.config(bg=bg_color, fg=fg_color)
        self.ping_label.config(bg=bg_color, fg=fg_color)
        self.ping_entry.config(bg=bg_color, fg=fg_color, insertbackground=fg_color)
        self.ping_button.config(bg=bg_color, fg=fg_color)
        self.progress.config(style="TProgressbar")

        # Apply theme to progress bar
        style = ttk.Style()
        style.configure("TProgressbar", background=fg_color, troughcolor=bg_color, thickness=20)

        # Apply theme to other widgets if needed
        self.ping_window_widgets = []

    def change_font_size(self):
        size = simpledialog.askinteger("Font Size", "Enter new font size:", initialvalue=self.font_size.get())
        if size:
            self.font_size.set(size)
            self.label_ip.config(font=("Helvetica", self.font_size.get()))
            self.label_isp.config(font=("Helvetica", self.font_size.get()))
            self.label_status.config(font=("Helvetica", self.font_size.get()))
            self.label_speed.config(font=("Helvetica", self.font_size.get()))

    # Function to update the GUI with new IP and status
    def update_network_status(self, ip, isp, speed, is_connected, net_info):
        # Update IP address label
        ip_text = f"IP Address: {ip}" if ip else "IP Address: N/A"
        self.label_ip.config(text=ip_text)

        # Update ISP label
        isp_text = f"ISP: {isp}" if isp else "ISP: N/A"
        self.label_isp.config(text=isp_text)

        # Update internet status
        status_text = "Internet: Connected" if is_connected else "Internet: Disconnected"
        self.label_status.config(text=status_text)

        # Update network info
        net_info_text = f"Network Info: {net_info}"
        self.label_netinfo.config(text=net_info_text)

        # Track the current network status and store it in the history
        self.add_to_history(ip, isp, speed, is_connected)

        # Update the history in the new window (if it's open)
        if hasattr(self, 'history_window') and self.history_window.winfo_exists():
            self.update_history_tree()

        # Prepare data for the table
        table_data = [
            ["IP Address", ip],
            ["ISP", isp],
            ["Speed", speed],
            ["Status", is_connected],
            ["Network Info", net_info]
        ]

        # Print the table using tabulate
        print(tabulate.tabulate(table_data, headers=["Property", "Value"]))
        print("-------------------------------------------------------------------------------------------------------------------------------")

    # Function to run a fake progress bar for refreshing network status
    def run_fake_refresh(self):
        self.progress["value"] = 0  # Reset progress bar
        self.fake_progress(100)  # Start fake progress bar
        self.root.after(2000, self.manual_refresh)  # Simulate a 2-second delay before refreshing
        self.progress["value"] = 0  # Reset progress bar

    # Function to run the speed test with a fake progress bar
    def run_fake_speed_test(self):
        self.progress["value"] = 0  # Reset progress bar
        self.fake_progress(100)  # Start fake progress bar
        self.root.after(3000, self.run_speed_test)  # Simulate a 3-second delay for speed test
        self.progress["value"] = 0  # Reset progress bar

    # Function to simulate fake progress
    def fake_progress(self, goal):
        current_value = self.progress["value"]
        if current_value < goal:
            self.progress["value"] = current_value + 5  # Increment the progress
            self.root.after(500, self.fake_progress, goal)  # Update every 250 ms

    def run_speed_test(self):
        threading.Thread(target=self._run_speed_test_thread, daemon=True).start()
        

    def _run_speed_test_thread(self):
        print("Running speed test...")
        download_speed, upload_speed = get_internet_speed()
        if download_speed is not None and upload_speed is not None:
            print(f"Download Speed: {download_speed}, Upload Speed: {upload_speed}")
            speed_text = f"Speed: {download_speed:.2f} Mbps (Download), {upload_speed:.2f} Mbps (Upload)"
            
            # Schedule GUI updates on the main thread
            self.root.after(0, self._update_history_and_label, self.public_ip, self.isp_info, (download_speed, upload_speed), self.is_connected, speed_text)
        else:
            print(f"Speed test failed.")
            speed_text = "Speed: N/A"
            
            # Schedule GUI updates on the main thread
            self.root.after(0, self._update_label_only, speed_text)

    def _update_history_and_label(self, public_ip, isp, speed, is_connected, speed_text):
        self.add_to_history(public_ip, isp, speed, is_connected)
        if hasattr(self, 'history_window') and self.history_window.winfo_exists():
            self.update_history_tree()
        self._update_label_only(speed_text)

    def _update_label_only(self, speed_text):
        self.label_speed.config(text=speed_text)

        
    # Monitor network status every 10 minutes and update GUI
    def monitor_network_changes(self):
        # Use a background thread to avoid blocking the GUI
        threading.Thread(target=self._monitor_network_thread, daemon=True).start()

    # This will run in a background thread
    def _monitor_network_thread(self):
        public_ip = get_public_ip()  # Get public IP address
        local_ip = get_local_ip()  # Get local IP address
        is_connected = public_ip is not None  # Check if there's an internet connection
        isp_info = get_isp_info(public_ip) if is_connected else "N/A"  # Get ISP info if connected
        net_info = get_network_info()  # Get local network info

        # Check if there is an internet connection
        if not is_connected:
            # Log the network status to a CSV file
            self.log_network_history_to_csv()

            # Send an email alert about the disconnection
            self.send_email(
                subject="Internet Disconnection Alert",
                body=f"Internet disconnected at {datetime.datetime.now()}",
                recipient_email="admin@example.com",
                attached_file="network_history.csv"
            )
        else:
            # Run the speed test in a separate thread to avoid blocking the GUI
            speed_thread = threading.Thread(target=self._run_speed_test_thread, daemon=True)
            speed_thread.start()

            # Check if the speed is below the threshold (e.g., 5 Mbps)
            download_speed, upload_speed = get_internet_speed()
            if download_speed and upload_speed is not None and download_speed and upload_speed < 1000:
                # Log the network status to a CSV file
                self.log_network_history_to_csv()

                # Send an email alert about the slow speed
                self.send_email(
                    subject="Slow Internet Alert",
                    body=f"Internet speed is slow: {download_speed:.2f} Mbps at {datetime.datetime.now()}",
                    recipient_email="jasonereso.nextvas@gmail.com",
                    attached_file="network_history.csv"
                )

        # Update the GUI (must be done on the main thread using `after`)
        self.root.after(0, self.update_network_status, public_ip, isp_info, download_speed, is_connected, net_info)

        # Schedule the next network check after 10 minutes (on the main thread)
        self.root.after(600000, self.monitor_network_changes)


    # This will run in a background thread
    # def _monitor_network_thread(self):
    #     public_ip = get_public_ip()  # Get public IP address
    #     local_ip = get_local_ip()  # Get local IP address
    #     is_connected = public_ip is not None  # Check if there's an internet connection
    #     isp_info = get_isp_info(public_ip) if is_connected else "N/A"  # Get ISP info if connected
    #     net_info = get_network_info()  # Get local network info

    #     # Run speed test in a separate thread to avoid blocking the GUI
    #     speed_thread = threading.Thread(target=self._run_speed_test_thread, daemon=True)
    #     speed_thread.start()


    #     # Update the GUI (must be done on the main thread using `after`)
    #     self.root.after(0, self.update_network_status, public_ip, isp_info, None, is_connected, net_info)

    #     # Schedule the next network check after 10 minutes (on the main thread)
    #     self.root.after(600000, self.monitor_network_changes)

    # Function to manually refresh the network status when the button is pressed
    def manual_refresh(self):
        # Use a background thread to avoid freezing the GUI
        threading.Thread(target=self._manual_refresh_thread, daemon=True).start()

    # Function to manually refresh the network status when the button is pressed
    def _manual_refresh_thread(self):
        print("Manual refresh triggered")
        time.sleep(10)
        print("Manual refresh Successful!")
        # Update the network information after the delay
        self.root.after(0, self.monitor_network_changes)

    # Function to open a new window for continuous ping
    def open_ping_window(self):
        address = self.ping_entry.get()  # Get the address entered by the user
        if not address:
            return  # Do nothing if no address is entered

        # Create a new window
        self.ping_window = tk.Toplevel(self.root)
        self.ping_window.title(f"Pinging: {address}")

        # Apply theme to the new window
        self.apply_theme_to_window(self.ping_window)

        # Label to show live ping results
        self.ping_result_label = tk.Label(self.ping_window, text="Pinging...", font=("Helvetica", 12))
        self.ping_result_label.pack(pady=10)

        # Start pinging the entered address
        # self.ping_continuously(address)

        # Start pinging the entered address in a separate thread
        self.ping_stop_event = threading.Event()
        self.ping_thread = threading.Thread(target=self.ping_continuously, args=(address,), daemon=True)
        self.ping_thread.start()

        # Bind the window close event
        self.ping_window.protocol("WM_DELETE_WINDOW", self.on_ping_window_close)

    # Function to apply theme to a specific window
    def apply_theme_to_window(self, window):
        bg_color = "black" if self.theme.get() == "Dark" else "white"
        fg_color = "#F5F5DC" if self.theme.get() == "Dark" else "black"

        window.config(bg=bg_color)
        
        # Apply theme to all widgets in the window
        for widget in window.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=bg_color, fg=fg_color)
            elif isinstance(widget, tk.Entry):
                widget.config(bg=bg_color, fg=fg_color, insertbackground=fg_color)
            elif isinstance(widget, tk.Button):
                widget.config(bg=bg_color, fg=fg_color)

    # Function to continuously ping the address and update the label
    def ping_continuously(self, address):
        try:
            # Run the ping command (change '-n' to '-c' if on Linux/Mac)
            ping_process = subprocess.Popen(['ping', '-n', '1', address], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = ping_process.communicate()

            # Display the ping result in the GUI
            if ping_process.returncode == 0:
                ping_result = output
            else:
                ping_result = f"Ping failed: {error}"

            # Update the ping result label
            # self.ping_result_label.config(text=ping_result)
            self.root.after(0, self.update_ping_result, ping_result)

            # Print the ping result to the CLI
            print(ping_result)

        except Exception as e:
            ping_result = f"Error: {e}"
            # self.ping_result_label.config(text=ping_result)
            self.root.after(0, self.update_ping_result, ping_result)
            print(ping_result)  # Print error to CLI

        # # Schedule the next ping after 1 second (1000 milliseconds)
        self.ping_window.after(1000, self.ping_continuously, address)
        # time.sleep(1)

    def update_ping_result(self, result):
        if hasattr(self, 'ping_result_label') and self.ping_result_label.winfo_exists():
            self.ping_result_label.config(text=result)
    
    def on_ping_window_close(self):
        self.ping_stop_event.set()  # Signal the thread to stop
        self.ping_window.destroy()  # Close the window
    
    def export_to_csv(self):
        # Ask user for the file path
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return

        # Gather data to export
        data = [
            ["Label", "Value"],
            ["IP Address", self.label_ip.cget("text")],
            ["ISP", self.label_isp.cget("text")],
            ["Internet Status", self.label_status.cget("text")],
            ["Network Info", self.label_netinfo.cget("text")],
            ["Speed", self.label_speed.cget("text")],
        ]

        # Write data to CSV
        with open(file_path, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(data)

        print(f"Data exported to {file_path}")

    # Add new data to the history list
    def add_to_history(self, public_ip, isp, speed, is_connected):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        download_speed, upload_speed = speed if speed is not None else (None, None)

        history_entry = {
            "Timestamp": timestamp,
            "Public IP": public_ip or "N/A",
            "ISP": isp or "N/A",
            "Download Speed": f"{download_speed:.2f}" if download_speed else "N/A",
            "Upload Speed": f"{upload_speed:.2f}" if upload_speed else "N/A",
            "Connected": "Yes" if is_connected else "No"
        }
        self.network_history.append(history_entry)

    def open_history_window(self):
        # Create a new Toplevel window
        self.history_window = tk.Toplevel(self.root)
        self.history_window.title("Network History Nextvas")

        # Treeview widget to display history
        self.history_tree = ttk.Treeview(self.history_window, columns=("Timestamp", "Public IP", "ISP", "Download Speed", "Upload Speed", "Connected"))
        self.history_tree.heading("Timestamp", text="Timestamp")
        self.history_tree.heading("Public IP", text="Public IP")
        self.history_tree.heading("ISP", text="ISP")
        self.history_tree.heading("Download Speed", text="Download Speed (Mbps)")
        self.history_tree.heading("Upload Speed", text="Upload Speed (Mbps)")
        self.history_tree.heading("Connected", text="Connected")
        self.history_tree.pack(pady=40)

        # Insert the history data into the Treeview
        self.update_history_tree()

        # Add an export button in the history window
        export_button = tk.Button(self.history_window, text="Export to CSV", command=self.export_history_to_csv)
        export_button.pack(pady=10)

    # Update the Treeview widget with the latest history
    def update_history_tree(self):
        # Clear existing rows
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        
        # Insert updated history data into the TreeView
        for entry in self.network_history:
            self.history_tree.insert("", "end", values=(
                entry["Timestamp"],
                entry["Public IP"],
                entry["ISP"],
                entry["Download Speed"],  
                entry["Upload Speed"],   
                entry["Connected"]
            ))

    # Export the history to a CSV file
    def export_history_to_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return  # Do nothing if the user cancels the dialog

        # Write the history to a CSV file
        with open(file_path, "w", newline="") as csvfile:
            fieldnames = ["Timestamp", "Public IP", "ISP", "Download Speed", "Upload Speed", "Connected"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for entry in self.network_history:
                writer.writerow(entry)

    # Function to log network history into CSV
    def log_network_history_to_csv(self, filename="network_history.csv"):
        fieldnames = ["Timestamp", "Public IP", "ISP", "Download Speed", "Upload Speed", "Internet Status"]
        with open(filename, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.network_history:
                writer.writerow({
                    "Timestamp": entry["timestamp"],
                    "Public IP": entry["public_ip"],
                    "ISP": entry["isp"],
                    "Download Speed": entry["speed"][0] if entry["speed"] else "N/A",
                    "Upload Speed": entry["speed"][1] if entry["speed"] else "N/A",
                    "Internet Status": "Connected" if entry["is_connected"] else "Disconnected"
                })

    
# Start the GUI application
def start_gui():
    root = tk.Tk()
    # root.iconbitmap('path/to/your/icon.ico')
    app = NetworkMonitorApp(root)
    root.mainloop()

start_gui()
