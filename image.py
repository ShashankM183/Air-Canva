import cv2
import numpy as np
import mediapipe as mp
from collections import deque
import tkinter as tk
from tkinter import messagebox, simpledialog
import os
import bcrypt
from PIL import Image, ImageTk

# ----------------- User Management -------------------
users_file = "users.txt"
saved_dir = "saved_drawings"

def save_user(username, password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    with open(users_file, "a") as file:
        file.write(f"{username},{hashed.decode()}\n")

def user_exists(username, password):
    if not os.path.exists(users_file):
        return False
    with open(users_file, "r") as file:
        users = file.readlines()
        for user in users:
            try:
                stored_user, stored_hash = user.strip().split(",")
                if stored_user == username and bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode()):
                    return True
            except ValueError:
                continue
    return False

# ----------------- GUI Setup -------------------
root = tk.Tk()
root.title("Air Canvas Login")
root.attributes("-fullscreen", True)
root.configure(bg="#3498db")

tk.Label(root, text="Welcome to Air Canvas", font=("Arial", 24, "bold"), bg="#3498db", fg="white").pack(pady=20)

frame = tk.Frame(root, bg="#2980b9", padx=50, pady=50)
frame.pack()

tk.Label(frame, text="Username:", font=("Arial", 14), bg="#2980b9", fg="white").grid(row=0, column=0, pady=10)
entry_username = tk.Entry(frame, font=("Arial", 14))
entry_username.grid(row=0, column=1, pady=10)

tk.Label(frame, text="Password:", font=("Arial", 14), bg="#2980b9", fg="white").grid(row=1, column=0, pady=10)
entry_password = tk.Entry(frame, font=("Arial", 14), show="*")
entry_password.grid(row=1, column=1, pady=10)

def register():
    username = entry_username.get()
    password = entry_password.get()
    if username and password:
        if user_exists(username, password):
            messagebox.showerror("Error", "User already exists!")
        else:
            save_user(username, password)
            messagebox.showinfo("Success", "Registration successful! You can now log in.")
    else:
        messagebox.showerror("Error", "All fields are required!")

def login():
    username = entry_username.get()
    password = entry_password.get()
    if user_exists(username, password):
        root.destroy()
        start_air_canvas(username)
    else:
        messagebox.showerror("Error", "Invalid credentials!")

tk.Button(frame, text="Login", font=("Arial", 14), bg="#2ecc71", fg="white", command=login).grid(row=2, column=0, pady=20)
tk.Button(frame, text="Register", font=("Arial", 14), bg="#f39c12", fg="white", command=register).grid(row=2, column=1, pady=20)
tk.Button(root, text="Exit", font=("Arial", 14), bg="#e74c3c", fg="white", command=root.destroy).pack(pady=10)

# ----------------- Air Canvas -------------------
def start_air_canvas(username):
    if not os.path.exists(os.path.join(saved_dir, username)):
        os.makedirs(os.path.join(saved_dir, username))

    def save_drawing():
        name = simpledialog.askstring("Save Drawing", "Enter name of your drawing:")
        if name:
            path = os.path.join(saved_dir, username, f"{name}.png")
            cv2.imwrite(path, paintWindow)
            print(f"Saved to {path}")

    def show_gallery():
        gallery = tk.Tk()
        gallery.title("Recent Drawings")
        gallery.configure(bg="white")
        files = sorted(
            [f for f in os.listdir(os.path.join(saved_dir, username)) if f.endswith(".png")],
            key=lambda x: os.path.getctime(os.path.join(saved_dir, username, x)),
            reverse=True
        )[:5]

        for i, file in enumerate(files):
            img_path = os.path.join(saved_dir, username, file)
            img = Image.open(img_path)
            img = img.resize((200, 150))
            tk_img = ImageTk.PhotoImage(img)
            label = tk.Label(gallery, image=tk_img)
            label.image = tk_img
            label.grid(row=i // 3, column=i % 3, padx=10, pady=10)

        tk.Button(gallery, text="Close", command=gallery.destroy).pack(pady=10)
        gallery.mainloop()

    bpoints = [deque(maxlen=1024)]
    gpoints = [deque(maxlen=1024)]
    rpoints = [deque(maxlen=1024)]
    ypoints = [deque(maxlen=1024)]
    blue_index = green_index = red_index = yellow_index = 0

    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255)]
    colorIndex = 0

    global paintWindow
    paintWindow = np.ones((471, 636, 3), dtype=np.uint8) * 255

    button_area = [(40, "CLEAR", (0, 0, 0)), (160, "BLUE", (255, 0, 0)),
                   (275, "GREEN", (0, 255, 0)), (390, "RED", (0, 0, 255)),
                   (505, "YELLOW", (0, 255, 255))]

    for x, text, color in button_area:
        cv2.rectangle(paintWindow, (x, 1), (x + 95, 65), color, 2)
        cv2.putText(paintWindow, text, (x + 10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    cv2.namedWindow('Paint', cv2.WINDOW_AUTOSIZE)
    mpHands = mp.solutions.hands
    hands = mpHands.Hands(max_num_hands=1, min_detection_confidence=0.7)
    mpDraw = mp.solutions.drawing_utils
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        framergb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(framergb)

        for x, text, color in button_area:
            cv2.rectangle(frame, (x, 1), (x + 95, 65), color, 2)
            cv2.putText(frame, text, (x + 10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        if result.multi_hand_landmarks:
            landmarks = []
            for handlms in result.multi_hand_landmarks:
                for lm in handlms.landmark:
                    lmx, lmy = int(lm.x * 640), int(lm.y * 480)
                    landmarks.append([lmx, lmy])
                mpDraw.draw_landmarks(frame, handlms, mpHands.HAND_CONNECTIONS)

            fore_finger = tuple(landmarks[8])
            thumb = tuple(landmarks[4])
            cv2.circle(frame, fore_finger, 5, (0, 255, 0), -1)

            if abs(thumb[1] - fore_finger[1]) < 30:
                bpoints.append(deque(maxlen=1024))
                gpoints.append(deque(maxlen=1024))
                rpoints.append(deque(maxlen=1024))
                ypoints.append(deque(maxlen=1024))
                blue_index += 1
                green_index += 1
                red_index += 1
                yellow_index += 1
            elif fore_finger[1] <= 65:
                if 40 <= fore_finger[0] <= 140:
                    bpoints = [deque(maxlen=1024)]
                    gpoints = [deque(maxlen=1024)]
                    rpoints = [deque(maxlen=1024)]
                    ypoints = [deque(maxlen=1024)]
                    blue_index = green_index = red_index = yellow_index = 0
                    paintWindow[67:, :, :] = 255
                elif 160 <= fore_finger[0] <= 255:
                    colorIndex = 0
                elif 275 <= fore_finger[0] <= 370:
                    colorIndex = 1
                elif 390 <= fore_finger[0] <= 485:
                    colorIndex = 2
                elif 505 <= fore_finger[0] <= 600:
                    colorIndex = 3
            else:
                if colorIndex == 0:
                    bpoints[blue_index].appendleft(fore_finger)
                elif colorIndex == 1:
                    gpoints[green_index].appendleft(fore_finger)
                elif colorIndex == 2:
                    rpoints[red_index].appendleft(fore_finger)
                elif colorIndex == 3:
                    ypoints[yellow_index].appendleft(fore_finger)

        for i, points in enumerate([bpoints, gpoints, rpoints, ypoints]):
            for j in range(len(points)):
                for k in range(1, len(points[j])):
                    if points[j][k - 1] is None or points[j][k] is None:
                        continue
                    cv2.line(frame, points[j][k - 1], points[j][k], colors[i], 2)
                    cv2.line(paintWindow, points[j][k - 1], points[j][k], colors[i], 2)

        cv2.imshow("Output", frame)
        cv2.imshow("Paint", paintWindow)

        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_drawing()
        elif key == ord('g'):
            show_gallery()

    cap.release()
    cv2.destroyAllWindows()

root.mainloop()
