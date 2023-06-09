import os
import math
import copy
import tkinter as tk
from tkinter import filedialog
from tkinter import colorchooser
from functools import partial
import pkg_resources
import globalVars as gV

installed = {pkg.key for pkg in pkg_resources.working_set}
usePIL = False
if "pillow" in installed:
    usePIL = True
    from PIL import Image, ImageDraw


"""
Reads in files of acceptable focal points and yaw ranges and generates a 
plot of the acceptable camera positions.

Files are expected to be a sequence of lines with the following format:

focal_point_x,focal_point_z : yaw_range_1_start,yaw_range_1_end,yaw_range_2_start,yaw_range_2_end,...,yaw_range_n_start,yaw_range_n_end
                            ^
Note the colon separating the focal point entries from the yaw range entries.

Each line needs at least two entries for the focal point, and each valid
yaw range should include a start and end point. This means the total number 
of entries should be even. Furthermore, yaw ranges are assumed to travel
counter-clockwise from the start of the range to the end of the range, or
in the direction of increasing AU. To give some concrete examples of what 
I mean by this:

 - The range 16384 to 32768 will assume the quarter-circle range from +X to -Z
 - The range 49152 to 16284 will assume the half-circle range including +Z, NOT
   the half-circle range including -Z
 - The range 48005 to 48000 will include nearly the entire circle range, NOT the 
   small wedge between 48000 and 48005. 

Note that in the examples above I assume the following convention:
 - +Z is 0
 - +X is 16384
 - -Z is 32768
 - -X is 49152

The generated plot has bounds [-8192,8191] in X and Z, and is scaled down 
by a factor of 16 in each direction for easier generation/viewing. 
"""

# Creates the tkinter window that houses the program
def setup_window():
    gV.window = tk.Tk()
    gV.window.title("Van Halen Valid Camera Viewer")
    gV.window.geometry("1024x1024")
    gV.window.resizable(False, False)

# Creates the ribbon at the top of the window
def setup_menu_bar():
    if gV.window == None:
        setup_window()

    menu_bar = tk.Menu(master=gV.window)
    
    filemenu = tk.Menu(menu_bar, tearoff=0)
    filemenu.add_command(label="Add New FP/Yaw File", command=spawn_load_file_window)
    filemenu.add_command(label="Save FP/Yaw Info to File", command=spawn_save_file_window)
    if usePIL:
        filemenu.add_command(label="Save PNG", command=save_png)
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=gV.window.quit)
    menu_bar.add_cascade(label='File', menu=filemenu)

    editmenu = tk.Menu(menu_bar, tearoff=0)
    editmenu.add_checkbutton(label="Flip Yaws", command=flip_yaws)
    editmenu.add_separator()
    editmenu.add_command(label="Clear Focal Points", command=clear_existing_fps)
    editmenu.add_command(label="Clear Test Points", command=clear_existing_test_points)
    editmenu.add_command(label="Clear All", command=clear_all)
    menu_bar.add_cascade(label='Edit', menu=editmenu)

    testmenu = tk.Menu(menu_bar, tearoff=0)
    testmenu.add_command(label="Add Test Point", command=spawn_test_point_window)
    menu_bar.add_cascade(label='Test', menu=testmenu)

    settingsmenu = tk.Menu(menu_bar, tearoff=0)
    settingsmenu.add_command(label="Display Settings", command=spawn_display_settings_window)
    menu_bar.add_cascade(label='Settings', menu=settingsmenu)

    gV.window.config(menu=menu_bar)


# Spawns a file selection dialog box and loads the focal points from the chosen file
def spawn_load_file_window():
    filename = filedialog.askopenfilename(initialdir = "/",
                                          title = "Select a File",
                                          filetypes = (("Text files",
                                                        "*.txt*"),
                                                       ("all files",
                                                        "*.*")))
    
    new_fp_info = read_file(filename)

    for fp_and_yaw in new_fp_info:
        gV.fps_and_yaws.append(fp_and_yaw)
    
    draw_screen()

# Helper for reading in a list of focal points and associated acceptable yaws
def read_file(filename):
    fps_and_yaws = []
    with open(filename, "r") as file:
        line_counter = 0
        for line in file:
            line_counter += 1
            if line.strip() == "" or line.startswith("#"):
                continue
            linesplit = line.split(':')
            if len(linesplit) != 2:
                print("INVALID FORMAT: Invalid number of colons on line", str(line_counter) + "; should be one, but found " + str(len(linesplit) - 1) + "!")
                quit()

            fp_strings = linesplit[0].split(',')
            if len(fp_strings) != 2:
                print("INVALID FORMAT: Found invalid number of focal point entries on line ", line_counter)
                quit()
            fp = float(fp_strings[0]), float(fp_strings[1])

            yaw_strings = linesplit[1].split(',')
            if len(yaw_strings) % 2 != 0:
                print("INVALID FORMAT: Found non-even number of yaw range entries on line ", line_counter)
                quit()
            yaws = []
            for i in range(int(len(yaw_strings)/2)):
                yaws.append((int(yaw_strings[2*i]), int(yaw_strings[2*i+1])))

            fps_and_yaws.append((fp, yaws))

    return fps_and_yaws

# Spawns a file selection dialog box and loads the focal points from the chosen file
def spawn_save_file_window():
    filename = filedialog.asksaveasfilename(initialfile = 'Untitled.txt',
                                        defaultextension=".txt",
                                        filetypes=[("All Files","*.*"),
                                                   ("Text Documents","*.txt")])
    
    save_file(filename)

# Helper for saving out a list of focal points and associated acceptable yaws
def save_file(filename):
    with open(filename, "w") as file:
        for fp, yaw_ranges in gV.fps_and_yaws:
            file.write(str(fp[0]) + ',' + str(fp[1]) + ":")
            yaw_str = ""
            for yaw_range in yaw_ranges:
                yaw_str += str(yaw_range[0]) + ',' + str(yaw_range[1]) + ','
            yaw_str = yaw_str[:-1]
            file.write(yaw_str + '\n')

# Helper for saving canvas as a PNG image
def save_png():
    filename = filedialog.asksaveasfilename(initialfile = 'Untitled.png',
                                        defaultextension=".png",
                                        filetypes=[("All Files","*.*"),
                                                   ("PNG Image Files","*.png")])
    
    if filename is None or filename == "":
        return

    output = Image.new("RGB", (1024, 1024), gV.display_settings["background_color"])
    draw = ImageDraw.Draw(output)

    # Draw Polygons
    for fp, yaw_ranges in gV.fps_and_yaws:
        for yaw_range in yaw_ranges:
            polygon_points = find_polygon(fp, yaw_range)
            screen_polygon_points = mario_to_screen(polygon_points)

            draw.polygon(screen_polygon_points, 
                         outline=gV.display_settings["valid_position_color"], 
                         fill=gV.display_settings["valid_position_color"])

    # Draw Test Points
    true_points, false_points = get_valid_invalid_points()

    true_sps = mario_to_screen(true_points)
    false_sps = mario_to_screen(false_points)

    for sp in true_sps:
        gV.shapes.append(draw.ellipse([int(sp[0] - gV.display_settings["test_point_diameter"]/2), 
                                      int(sp[1] - gV.display_settings["test_point_diameter"]/2),
                                      int(sp[0] + gV.display_settings["test_point_diameter"]/2),
                                      int(sp[1] + gV.display_settings["test_point_diameter"]/2)],
                                      outline=gV.display_settings["test_point_success_color"],
                                      fill=gV.display_settings["test_point_success_color"]))
    for sp in false_sps:
        gV.shapes.append(draw.ellipse([int(sp[0] - gV.display_settings["test_point_diameter"]/2), 
                                      int(sp[1] - gV.display_settings["test_point_diameter"]/2),
                                      int(sp[0] + gV.display_settings["test_point_diameter"]/2),
                                      int(sp[1] + gV.display_settings["test_point_diameter"]/2)],
                                      outline=gV.display_settings["test_point_failure_color"],
                                      fill=gV.display_settings["test_point_failure_color"]))
    
    output.save(filename)

# Clears all focal point/yaw information and redraws the screen
def clear_existing_fps():
    gV.fps_and_yaws = []
    draw_screen()

# Clears all test points and redraws the screen
def clear_existing_test_points():
    gV.points = []
    draw_screen()

# Clears everything and redraws the screen
def clear_all():
    gV.fps_and_yaws = []
    gV.points = []
    draw_screen()

# Spawns the 'Add Test Points' window
def spawn_test_point_window():
    tp_window = tk.Toplevel(gV.window)
    tp_window.title("Add a Test Point")
    tp_window.geometry("300x120")
 
    title_frame = tk.Frame(tp_window)
    title_frame.pack(pady=(10,5))
    tk.Label(title_frame, text ="Enter a test point:").pack()

    coords_frame = tk.Frame(tp_window)
    coords_frame.pack()

    x_frame = tk.Frame(coords_frame)

    x_label = tk.Label(x_frame,text="X").pack(side=tk.TOP)
    x_entry = tk.Entry(x_frame, width=20)
    x_entry.insert(0,"0")
    x_entry.pack(side=tk.TOP)

    z_frame = tk.Frame(coords_frame)

    z_label = tk.Label(z_frame,text="Z").pack(side=tk.TOP)
    z_entry = tk.Entry(z_frame, width=20)
    z_entry.insert(0,"0")
    z_entry.pack(side=tk.TOP)

    x_frame.pack(padx=5,side=tk.LEFT)
    z_frame.pack(padx=5,side=tk.LEFT)

    button_frame = tk.Frame(tp_window)
    button_frame.pack(pady=(10,10))
    
    add_button = tk.Button(button_frame, text="Add Test Point", command=partial(add_test_point, x_entry, z_entry))
    add_button.pack(side=tk.RIGHT)
    
# Helper for adding a test point to the list of test points
def add_test_point(x_entry : tk.Entry, z_entry : tk.Entry):
    if x_entry is None or z_entry is None:
        print("BUG: Entries are none!")
        return
    x_val = x_entry.get()
    z_val = z_entry.get()
    if x_val is not None and z_val is not None:
        try:
            gV.points.append((float(x_val), float(z_val)))
            draw_screen()
        except:
            spawn_popup("Invalid Format Warning!", "X/Z values must be valid numbers.")

# Spawns a popup window with the specified title and message
def spawn_popup(title : str, message : str):
   top= tk.Toplevel(gV.window)
   top.geometry("300x80")
   top.title(title) 

   tk.Label(top, text=message).pack(pady=10)
   tk.Button(top, text="OK", command=top.destroy).pack(pady=10)         

# Spawns the display 
def spawn_display_settings_window():
    ds_window = tk.Toplevel(gV.window)
    ds_window.title("Display Settings")
    ds_window.geometry("250x250")
    ds_window.resizable(False, False)

    # Background Color
    setup_color_setting(ds_window, "Background Color: ", "background_color", "Choose a new background color...")

    # Valid Position Color
    setup_color_setting(ds_window, "Valid Position Color: ", "valid_position_color", "Choose a new valid position color...")

    # Test Point Diameter Size
    tp_diameter_frame = tk.Frame(ds_window)
    tp_diameter_frame.pack(pady=10, anchor="w")

    tk.Label(tp_diameter_frame, text="Test Point Diameter: ").pack(side=tk.LEFT, padx=5, anchor="w")
    diameter_str = tk.StringVar()
    diameter_entry = tk.Entry(tp_diameter_frame, width=10, textvariable=diameter_str)
    diameter_entry.bind("<KeyRelease>", )
    diameter_entry.insert(0, str(gV.display_settings["test_point_diameter"]))
    diameter_entry.pack(side=tk.LEFT, anchor="e")

    # Test Point Successful Color
    setup_color_setting(ds_window, "Test Point Color (Valid): ", "test_point_success_color", "Choose a new valid test point color...")

    # Test Point Successful Color
    setup_color_setting(ds_window, "Test Point Color (Invalid): ", "test_point_failure_color", "Choose a new invalid test point color...")

    # Bottom Button Frame
    button_frame = tk.Frame(ds_window)
    button_frame.pack(pady=10, side=tk.RIGHT, anchor="e")

    ok_button = tk.Button(button_frame, text="OK", width=10, height=4, command=partial(save_display_settings, ds_window, diameter_str))
    cancel_button = tk.Button(button_frame, text="Cancel", width=10, height=4, command=ds_window.destroy) 

    cancel_button.pack(side=tk.RIGHT, padx=5, anchor="e")
    ok_button.pack(side=tk.RIGHT, padx=5, anchor="e") 

    gV.old_diplay_settings = copy.deepcopy(gV.display_settings)

    ds_window.focus_force()
    ds_window.grab_set()  

# Helper for setting up a color setting option in the display settings window
def setup_color_setting(ds_window : tk.Toplevel, label_text : str, settings_entry : str, color_dialog_title : str):
    setting_frame = tk.Frame(ds_window)
    setting_frame.pack(pady=10, anchor="w")

    tk.Label(setting_frame, text=label_text).pack(side=tk.LEFT, padx=5, anchor="w")
    color_button = tk.Button(setting_frame, width=10, borderwidth=0, highlightthickness=0, 
                             bg=gV.display_settings[settings_entry])
    color_button.configure(command=partial(change_display_color_setting, 
                                              ds_window, color_button, 
                                              settings_entry, color_dialog_title))
    color_button.pack(side=tk.LEFT, anchor="e")

# Callback for color settings in the display settings
def change_display_color_setting(ds_window : tk.Toplevel, color_button : tk.Button, settings_entry : str, dialog_title : str):
    ds_window.grab_release()
    output = colorchooser.askcolor(title=dialog_title, parent=ds_window)
    if output[1] is not None:
        gV.display_settings[settings_entry] = output[1]
        color_button.configure(bg=output[1])

    ds_window.focus_force()
    ds_window.grab_set()    

# Helper for saving display settings
def save_display_settings(ds_window : tk.Toplevel, diameter_str : tk.StringVar):
    
    # Save Display Diameter
    if not save_display_test_point_diameter(diameter_str):
        spawn_popup("Invalid Format Warning!", "Diameter must be a positive number.")
        gV.display_settings = gV.old_display_settings
        return
    
    # If all save functions returned true, close settings window
    ds_window.destroy()

# Helper for saving display diameter
def save_display_test_point_diameter(diameter_str : tk.StringVar):
    if diameter_str is None:
        print("BUG: Entries are none!")
        return False
    val = diameter_str.get()
    if val is not None:
        try:
            diam_val = float(val)
            if diam_val <= 0:
                return False
            gV.display_settings['test_point_diameter'] = diam_val
            draw_screen()
            return True

        except Exception as e:
            return False
    return False

# Enables/disables a 180 degree flip of the yaws
def flip_yaws():
    gV.flipped = not gV.flipped
    draw_screen()

# Helper for wrapping yaw values around
def wrap_yaw(yaw):
    while yaw < 0:
        yaw += 65536
    while yaw > 65535:
        yaw -= 65536
    return yaw

# Helper for converting points in Mario X/Z to screen coordinates X/Y
def mario_to_screen(pts):
    screen_pts = []
    for pt in pts:
        screen_pts.append((pt[0] / 16 + 512, pt[1] / 16 + 512))
    return screen_pts

# Helper for computing the squared Euclidean distance between points
def point_dist_squared(p1, p2):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

# Helper for computing relative yaw from one point, p1, to another point, p2
def compute_p2p_yaw(p1, p2):
    return wrap_yaw(16384 - int(math.atan2(p2[1] - p1[1], p2[0] - p1[0]) / math.pi * 32768))

# Helper function for computing whether a yaw is within a yaw range
def yaw_within_yaw_range(yaw, yaw_range):
    if yaw_range[0] <= yaw_range[1]:
        # Case 1: No wrap around
        return yaw >= yaw_range[0] and yaw <= yaw_range[1]
    else:
        # Case 2: Wrap around 
        return yaw >= yaw_range[0] or yaw <= yaw_range[1]

# Helper for finding where a yaw line propogating from a focal point hits the boundary of the map
def find_point_along_yaw_at_map_bounds(fp, yaw):
    if yaw == 0:
        return (fp[0], 8192)
    elif yaw == 16384:
        return (8192, fp[1])
    elif yaw == 32768:
        return (fp[0], -8192)
    elif yaw == 49152:
        return (-8192, fp[1])
    else:
        angle = wrap_yaw(16384 - yaw)/ 32768 * math.pi
        slope = math.tan(angle)

        if angle < math.pi / 2:
            p1 = (8192, fp[1] + slope * (8192 - fp[0]))
            p2 = (fp[0] + (8192 - fp[1]) / slope, 8192)
        elif angle < math.pi:
            p1 = (-8192, fp[1] + slope * (-8192 - fp[0]))
            p2 = (fp[0] + (8192 - fp[1]) / slope, 8192)
        elif angle < 3 * math.pi / 2:
            p1 = (-8192, fp[1] + slope * (-8192 - fp[0]))
            p2 = (fp[0] + (-8192 - fp[1]) / slope, -8192)
        else:
            p1 = (8192, fp[1] + slope * (8192 - fp[0]))
            p2 = (fp[0] + (-8192 - fp[1]) / slope, -8192)

        p1_dist = point_dist_squared(fp, p1)
        p2_dist = point_dist_squared(fp, p2)

        return p1 if p1_dist < p2_dist else p2

# Helper for finding corner points enclosed by a yaw range    
def find_enclosed_corner_points(fp, yaw_range):
    yaw_adjusted_range = [wrap_yaw(yaw_range[0] + (0 if gV.flipped else 32768)), 
                          wrap_yaw(yaw_range[1] + (0 if gV.flipped else 32768))]

    corner_points = [(-8192, -8192),
                     (-8192, 8192),
                     (8192, 8192),
                     (8192, -8192)]
    
    corner_point_yaws = []
    for cp in corner_points:
        yaw = compute_p2p_yaw(fp, cp)
        corner_point_yaws.append(yaw)

    enclosed_corner_points = []
    corner_counter = 0
    for cpy in corner_point_yaws:
        # Two cases: range wraps around or doesn't wrap around
        if yaw_within_yaw_range(cpy, yaw_adjusted_range):
            enclosed_corner_points.append(corner_points[corner_counter])
        
        corner_counter += 1

    return enclosed_corner_points

# Helper for finding the polygon corresponding to a focal point and yaw range
def find_polygon(fp, yaw_range):
    # Determine the yaw slope points
    p1 = find_point_along_yaw_at_map_bounds(fp, wrap_yaw(yaw_range[0] + (0 if gV.flipped else 32768)))
    p2 = find_point_along_yaw_at_map_bounds(fp, wrap_yaw(yaw_range[1] + (0 if gV.flipped else 32768)))

    # Check for corner points
    enclosed_corner_points = find_enclosed_corner_points(fp, yaw_range)

    polygon_points = [fp, p1]
    for ecp in enclosed_corner_points:
        polygon_points.append(ecp)
    polygon_points.append(p2)
    polygon_points.append(fp)

    return polygon_points

# Helper for evaluating all test points as valid/invalid
def get_valid_invalid_points():
    true_points = []
    false_points = copy.deepcopy(gV.points)

    for fp, yaw_ranges in gV.fps_and_yaws:
        new_true_points = []
        for tp in false_points:
            yaw = compute_p2p_yaw(fp, tp) if gV.flipped else compute_p2p_yaw(tp, fp)
            for yaw_range in yaw_ranges:
                if yaw_within_yaw_range(yaw, yaw_range):
                    new_true_points.append(tp)
                    break 
        for tp in new_true_points:
            true_points.append(tp)
            false_points.remove(tp)
    
    return true_points, false_points

# Draws all camera regions specified by 'focal_points_and_yaws' to the screen
def draw_screen():
    # Clear existing canvas
    for shape in gV.shapes:
        canvas.delete(shape)

    canvas.configure(bg=gV.display_settings["background_color"])
    gV.shapes = []
    
    # Draw Polygons
    for fp, yaw_ranges in gV.fps_and_yaws:
        for yaw_range in yaw_ranges:
            polygon_points = find_polygon(fp, yaw_range)
            screen_polygon_points = mario_to_screen(polygon_points)

            gV.shapes.append(canvas.create_polygon(screen_polygon_points, 
                                                   outline=gV.display_settings["valid_position_color"], 
                                                   fill=gV.display_settings["valid_position_color"]))

    # Draw Test Points
    true_points, false_points = get_valid_invalid_points()

    true_sps = mario_to_screen(true_points)
    false_sps = mario_to_screen(false_points)

    for sp in true_sps:
        gV.shapes.append(canvas.create_oval(int(sp[0] - gV.display_settings["test_point_diameter"]/2), 
                                            int(sp[1] - gV.display_settings["test_point_diameter"]/2),
                                            int(sp[0] + gV.display_settings["test_point_diameter"]/2),
                                            int(sp[1] + gV.display_settings["test_point_diameter"]/2),
                                            outline=gV.display_settings["test_point_success_color"], 
                                            fill=gV.display_settings["test_point_success_color"]))
    for sp in false_sps:
        gV.shapes.append(canvas.create_oval(int(sp[0] - gV.display_settings["test_point_diameter"]/2), 
                                            int(sp[1] - gV.display_settings["test_point_diameter"]/2),
                                            int(sp[0] + gV.display_settings["test_point_diameter"]/2),
                                            int(sp[1] + gV.display_settings["test_point_diameter"]/2),
                                            outline=gV.display_settings["test_point_failure_color"],
                                            fill=gV.display_settings["test_point_failure_color"]))

# Main Code

# Create TKinter Window/Canvas     
setup_window()

setup_menu_bar()

canvas_frame = tk.Frame()

canvas = tk.Canvas(master=canvas_frame)
canvas.configure(bg=gV.display_settings["background_color"])
canvas.pack(fill = tk.BOTH, expand = 1)  

canvas_frame.pack(fill = tk.BOTH, expand = 1)

draw_screen()

gV.window.mainloop()
