import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import mysql.connector


db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Richu@12",
    database="court_booking",
)
cursor = db.cursor()


ADMIN_PASSWORD = "admin123"
admin_logged_in = False



def get_courts():
    cursor.execute("SELECT court_id, court_name FROM courts")
    return cursor.fetchall()


def get_time_slots():
    cursor.execute("SELECT slot_id, slot_time FROM time_slots")
    return cursor.fetchall()


def is_available(court_id, slot_id, date):
    cursor.execute(
        "SELECT COUNT(*) FROM bookings "
        "WHERE court_id = %s AND slot_id = %s AND booking_date = %s",
        (court_id, slot_id, date),
    )
    count = cursor.fetchone()[0]
    return count == 0


def is_available_except(court_id, slot_id, date, booking_id):
    """Same as is_available(), but ignores one booking (the one being edited),
    so a booking never counts as clashing with itself."""
    cursor.execute(
        "SELECT COUNT(*) FROM bookings "
        "WHERE court_id = %s AND slot_id = %s AND booking_date = %s "
        "AND booking_id <> %s",
        (court_id, slot_id, date, booking_id),
    )
    count = cursor.fetchone()[0]
    return count == 0


def get_all_bookings():
    
    cursor.execute(
        "SELECT b.booking_id, b.student_id, b.student_name, c.court_name, "
        "b.booking_date, t.slot_time "
        "FROM bookings b "
        "JOIN courts c ON b.court_id = c.court_id "
        "JOIN time_slots t ON b.slot_id = t.slot_id "
        "ORDER BY b.booking_date, t.slot_time"
    )
    return cursor.fetchall()


def renumber_bookings():
    """Close the gaps in booking_id (1, 2, 3...) after a cancellation."""
    cursor.execute("SET @n = 0")
    cursor.execute("UPDATE bookings SET booking_id = (@n := @n + 1) ORDER BY booking_id")
    cursor.execute("ALTER TABLE bookings AUTO_INCREMENT = 1")
    db.commit()



def format_date(value):
    """Turn a database date (2026-12-25) into DD-MM-YYYY (25-12-2026) for display."""
    return value.strftime("%d-%m-%Y")


def fill_table(table, rows, date_index):
    """Empty a table, then fill it with rows. date_index = which column holds the date."""
    for item in table.get_children():
        table.delete(item)

    for row in rows:
        values = [str(item) for item in row]
        values[date_index] = format_date(row[date_index])
        table.insert("", tk.END, values=values)



def make_booking():
    student_id = student_id_entry.get().strip()
    name = name_entry.get().strip()
    court_text = court_box.get()
    slot_text = slot_box.get()
    date_text = date_entry.get().strip().replace(" ", "")

    
    if student_id == "" or name == "" or court_text == "" or slot_text == "" or date_text == "":
        messagebox.showwarning("Missing details", "Please fill in every field.")
        return

    
    try:
        date = datetime.strptime(date_text, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Invalid date", "Please enter the date as DD-MM-YYYY, e.g. 25-12-2026.")
        return

    
    court_choice = str(court_lookup[court_text])
    slot_choice = str(slot_lookup[slot_text])

    try:
        if is_available(court_choice, slot_choice, date):
            cursor.execute(
                "INSERT INTO bookings (student_id, student_name, court_id, slot_id, booking_date) "
                "VALUES (%s, %s, %s, %s, %s)",
                (student_id, name, court_choice, slot_choice, date),
            )
            db.commit()
            messagebox.showinfo("Success", "Booking confirmed!")
            clear_booking_form()
            view_bookings()
        else:
            messagebox.showwarning("Unavailable", "Sorry, that slot is already booked.")
    except mysql.connector.Error as error:
        messagebox.showerror("Database error", str(error))


def clear_booking_form():
    student_id_entry.delete(0, tk.END)
    name_entry.delete(0, tk.END)
    date_entry.delete(0, tk.END)
    court_box.set("")
    slot_box.set("")



def view_bookings():
    rows = get_all_bookings()
    fill_table(view_table, rows, 4)

    if len(rows) == 0:
        view_status.config(text="No bookings yet.")
    else:
        view_status.config(text=f"{len(rows)} booking(s) found.")



def find_bookings():
    global searched_student_id
    student_id = cancel_id_entry.get().strip()

    if student_id == "":
        messagebox.showwarning("Missing ID", "Please enter your Student ID.")
        return

    cursor.execute(
        "SELECT b.booking_id, c.court_name, b.booking_date, t.slot_time "
        "FROM bookings b "
        "JOIN courts c ON b.court_id = c.court_id "
        "JOIN time_slots t ON b.slot_id = t.slot_id "
        "WHERE b.student_id = %s",
        (student_id,),
    )
    rows = cursor.fetchall()
    fill_table(cancel_table, rows, 2)

    if len(rows) == 0:
        searched_student_id = ""
        messagebox.showinfo("Not found", "No bookings found for this ID.")
        return

    searched_student_id = student_id


def cancel_booking():
    selected = cancel_table.selection()
    if not selected:
        messagebox.showwarning("Nothing selected", "Click a booking in the list first.")
        return

    student_id = searched_student_id
    choice = cancel_table.item(selected[0])["values"][0]

    if not messagebox.askyesno("Confirm", "Are you sure you want to cancel this booking?"):
        return

    cursor.execute(
        "DELETE FROM bookings WHERE booking_id = %s AND student_id = %s",
        (choice, student_id),
    )
    db.commit()

    if cursor.rowcount > 0:
        renumber_bookings()
        messagebox.showinfo("Cancelled", "Booking cancelled.")
    else:
        messagebox.showerror("Error", "Invalid booking ID.")

    find_bookings()
    view_bookings()



def admin_login():
    global admin_logged_in
    if admin_password_entry.get() == ADMIN_PASSWORD:
        admin_logged_in = True
        admin_password_entry.delete(0, tk.END)
        login_frame.pack_forget()
        admin_frame.pack(fill="both", expand=True)
        admin_refresh()
    else:
        messagebox.showerror("Access denied", "Incorrect password.")
        admin_password_entry.delete(0, tk.END)


def admin_logout():
    global admin_logged_in
    admin_logged_in = False
    admin_frame.pack_forget()
    login_frame.pack(expand=True)


def admin_refresh():
    rows = get_all_bookings()
    fill_table(admin_table, rows, 4)

    if len(rows) == 0:
        admin_status.config(text="No bookings yet.")
    else:
        admin_status.config(text=f"{len(rows)} booking(s) found.")


def admin_delete():
    selected = admin_table.selection()
    if not selected:
        messagebox.showwarning("Nothing selected", "Click a booking in the list first.")
        return

    booking_id = admin_table.item(selected[0])["values"][0]

    if not messagebox.askyesno("Confirm", f"Delete booking {booking_id}? This cannot be undone."):
        return

    
    cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
    db.commit()

    if cursor.rowcount > 0:
        renumber_bookings()
        messagebox.showinfo("Deleted", "Booking deleted.")
    else:
        messagebox.showerror("Error", "Booking not found.")

    admin_refresh()
    view_bookings()


def admin_edit():
    selected = admin_table.selection()
    if not selected:
        messagebox.showwarning("Nothing selected", "Click a booking in the list first.")
        return

    values = admin_table.item(selected[0])["values"]
    booking_id = values[0]
    student_name = values[2]

    
    cursor.execute(
        "SELECT court_id, slot_id, booking_date FROM bookings WHERE booking_id = %s",
        (booking_id,),
    )
    row = cursor.fetchone()
    if row is None:
        messagebox.showerror("Error", "Booking not found.")
        admin_refresh()
        return
    old_court_id, old_slot_id, old_date = row

    
    edit_window = tk.Toplevel(window)
    edit_window.title(f"Edit Booking {booking_id}")
    edit_window.geometry("420x330")
    edit_window.configure(bg="#ffffff")
    edit_window.transient(window)
    edit_window.grab_set()

    form = ttk.Frame(edit_window, padding=20)
    form.pack(fill="both", expand=True)

    ttk.Label(form, text=f"Booking {booking_id}  -  {student_name}",
              font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))

    ttk.Label(form, text="Court:").grid(row=1, column=0, sticky="w", pady=8)
    edit_court = ttk.Combobox(form, values=list(court_lookup.keys()), state="readonly", width=24)
    edit_court.grid(row=1, column=1, pady=8, padx=10)

    ttk.Label(form, text="Time slot:").grid(row=2, column=0, sticky="w", pady=8)
    edit_slot = ttk.Combobox(form, values=list(slot_lookup.keys()), state="readonly", width=24)
    edit_slot.grid(row=2, column=1, pady=8, padx=10)

    ttk.Label(form, text="Date (DD-MM-YYYY):").grid(row=3, column=0, sticky="w", pady=8)
    edit_date = ttk.Entry(form, width=27)
    edit_date.grid(row=3, column=1, pady=8, padx=10)

    
    for text, court_id in court_lookup.items():
        if court_id == old_court_id:
            edit_court.set(text)
    for text, slot_id in slot_lookup.items():
        if slot_id == old_slot_id:
            edit_slot.set(text)
    edit_date.insert(0, format_date(old_date))

    def save_changes():
        court_text = edit_court.get()
        slot_text = edit_slot.get()
        date_text = edit_date.get().strip().replace(" ", "")

        if court_text == "" or slot_text == "" or date_text == "":
            messagebox.showwarning("Missing details", "Please fill in every field.", parent=edit_window)
            return

        try:
            date = datetime.strptime(date_text, "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Please enter the date as DD-MM-YYYY.", parent=edit_window)
            return

        court_choice = str(court_lookup[court_text])
        slot_choice = str(slot_lookup[slot_text])

        try:
            
            if is_available_except(court_choice, slot_choice, date, booking_id):
                cursor.execute(
                    "UPDATE bookings SET court_id = %s, slot_id = %s, booking_date = %s "
                    "WHERE booking_id = %s",
                    (court_choice, slot_choice, date, booking_id),
                )
                db.commit()
                messagebox.showinfo("Saved", "Booking updated.", parent=edit_window)
                edit_window.destroy()
                admin_refresh()
                view_bookings()
            else:
                messagebox.showwarning(
                    "Clash",
                    "That court is already booked at that time.\nPlease choose a different court, slot or date.",
                    parent=edit_window,
                )
        except mysql.connector.Error as error:
            messagebox.showerror("Database error", str(error), parent=edit_window)

    buttons = ttk.Frame(form)
    buttons.grid(row=4, column=0, columnspan=2, pady=20)
    ttk.Button(buttons, text="Save Changes", command=save_changes).pack(side="left", padx=5)
    ttk.Button(buttons, text="Cancel", command=edit_window.destroy).pack(side="left", padx=5)



def on_close():
    cursor.close()
    db.close()
    window.destroy()


window = tk.Tk()
window.title("University Court Booking")
window.geometry("900x560")
window.configure(bg="#f4f6f8")
window.protocol("WM_DELETE_WINDOW", on_close)

style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", background="#f4f6f8")
style.configure("TNotebook.Tab", padding=(18, 8), font=("Segoe UI", 10, "bold"))
style.configure("TFrame", background="#ffffff")
style.configure("TLabel", background="#ffffff", font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))


header = tk.Label(
    window,
    text="University Sports Court Booking",
    bg="#1f3a5f",
    fg="white",
    font=("Segoe UI", 16, "bold"),
    pady=14,
)
header.pack(fill="x")


notebook = ttk.Notebook(window)
notebook.pack(fill="both", expand=True, padx=12, pady=12)

tab_book = ttk.Frame(notebook, padding=20)
tab_view = ttk.Frame(notebook, padding=15)
tab_cancel = ttk.Frame(notebook, padding=15)
tab_admin = ttk.Frame(notebook, padding=15)
notebook.add(tab_book, text="  Make a Booking  ")
notebook.add(tab_view, text="  View Bookings  ")
notebook.add(tab_cancel, text="  Cancel a Booking  ")
notebook.add(tab_admin, text="  Admin  ")



court_lookup = {}
for court_id, court_name in get_courts():
    court_lookup[f"{court_id}. {court_name}"] = court_id

slot_lookup = {}
for slot_id, slot_time in get_time_slots():
    slot_lookup[f"{slot_id}. {slot_time}"] = slot_id

ttk.Label(tab_book, text="Student ID:").grid(row=0, column=0, sticky="w", pady=8)
student_id_entry = ttk.Entry(tab_book, width=30)
student_id_entry.grid(row=0, column=1, pady=8, padx=10)

ttk.Label(tab_book, text="Name:").grid(row=1, column=0, sticky="w", pady=8)
name_entry = ttk.Entry(tab_book, width=30)
name_entry.grid(row=1, column=1, pady=8, padx=10)

ttk.Label(tab_book, text="Court:").grid(row=2, column=0, sticky="w", pady=8)
court_box = ttk.Combobox(tab_book, values=list(court_lookup.keys()), state="readonly", width=27)
court_box.grid(row=2, column=1, pady=8, padx=10)

ttk.Label(tab_book, text="Time slot:").grid(row=3, column=0, sticky="w", pady=8)
slot_box = ttk.Combobox(tab_book, values=list(slot_lookup.keys()), state="readonly", width=27)
slot_box.grid(row=3, column=1, pady=8, padx=10)

ttk.Label(tab_book, text="Date (DD-MM-YYYY):").grid(row=4, column=0, sticky="w", pady=8)
date_entry = ttk.Entry(tab_book, width=30)
date_entry.grid(row=4, column=1, pady=8, padx=10)

ttk.Button(tab_book, text="Book Court", command=make_booking).grid(
    row=5, column=0, columnspan=2, pady=20
)


view_columns = ("ID", "Student ID", "Name", "Court", "Date", "Time")
view_table = ttk.Treeview(tab_view, columns=view_columns, show="headings", height=12)
for column in view_columns:
    view_table.heading(column, text=column)
    view_table.column(column, width=100, anchor="center")
view_table.column("ID", width=50)
view_table.pack(fill="both", expand=True)

view_status = ttk.Label(tab_view, text="")
view_status.pack(anchor="w", pady=(8, 0))

ttk.Button(tab_view, text="Refresh", command=view_bookings).pack(pady=8)



searched_student_id = ""

top_row = ttk.Frame(tab_cancel)
top_row.pack(fill="x", pady=(0, 10))
ttk.Label(top_row, text="Your Student ID:").pack(side="left")
cancel_id_entry = ttk.Entry(top_row, width=20)
cancel_id_entry.pack(side="left", padx=10)
ttk.Button(top_row, text="Find My Bookings", command=find_bookings).pack(side="left")

cancel_columns = ("Booking ID", "Court", "Date", "Time")
cancel_table = ttk.Treeview(tab_cancel, columns=cancel_columns, show="headings", height=10)
for column in cancel_columns:
    cancel_table.heading(column, text=column)
    cancel_table.column(column, width=130, anchor="center")
cancel_table.pack(fill="both", expand=True)

ttk.Button(tab_cancel, text="Cancel Selected Booking", command=cancel_booking).pack(pady=12)




login_frame = ttk.Frame(tab_admin)
login_frame.pack(expand=True)

ttk.Label(login_frame, text="Admin Login", font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))
ttk.Label(login_frame, text="Enter the admin password:").pack()
admin_password_entry = ttk.Entry(login_frame, width=28, show="*")
admin_password_entry.pack(pady=10)
admin_password_entry.bind("<Return>", lambda event: admin_login())
ttk.Button(login_frame, text="Log In", command=admin_login).pack(pady=5)


admin_frame = ttk.Frame(tab_admin)

admin_table = ttk.Treeview(admin_frame, columns=view_columns, show="headings", height=12)
for column in view_columns:
    admin_table.heading(column, text=column)
    admin_table.column(column, width=100, anchor="center")
admin_table.column("ID", width=50)
admin_table.pack(fill="both", expand=True)

admin_status = ttk.Label(admin_frame, text="")
admin_status.pack(anchor="w", pady=(8, 0))

button_row = ttk.Frame(admin_frame)
button_row.pack(pady=8)
ttk.Button(button_row, text="Edit Selected Booking", command=admin_edit).pack(side="left", padx=5)
ttk.Button(button_row, text="Delete Selected Booking", command=admin_delete).pack(side="left", padx=5)
ttk.Button(button_row, text="Refresh", command=admin_refresh).pack(side="left", padx=5)
ttk.Button(button_row, text="Log Out", command=admin_logout).pack(side="left", padx=5)



def on_tab_change(event):
    current_tab = notebook.index(notebook.select())

    if current_tab == 1:
        view_bookings()

    if current_tab != 3 and admin_logged_in:
        admin_logout()


notebook.bind("<<NotebookTabChanged>>", on_tab_change)

view_bookings()
window.mainloop()
