import tkinter as tk
from PIL import ImageGrab, ImageTk, Image
import requests
import os
from io import BytesIO

from predict_from_image import load_model, predict_from_image

'''
BIG PROBLEM: the app won't stay focused.
Potential solution: when you press F11 key, make the tkinter app back to focus again and show the full-screen image to do cropping


The app has two modes: initial mode and crop mode.

When user presses F11, crop mode will be activated. This means
1. the full screen will be captured as an image
2. this image is shown on the entire screen

Then, user can select a region. After the selection is done (when the mouse clicking is released), 
a "convert" button will be shown next to the cursor. 

If user clicks the "convert" button: [simpler version: do not show the button. Just right-click.]
the selected region will be fetched as an image. Then, send this image to the nougat OCR API to convert that 
into markdown language. [We will save this image in the images directory for now.] Remove the canvas to let user continuing reading.

Otherwise, user can just left-click anywhere else to reselect a region.

In crop mode, when the user presses ESC, then escape from crop mode to initial mode, but the app should still be running.
In initial mode, when the user presses ESC, the application ends.
'''

'''
second problem: crop region does not match selected region

(screen_width, screen_height): (1536, 864)
(PIL_image_width, PIL_image_height): (1920, 1080)

Solution:
adjust by ratio
'''

class ScreenCaptureApp:
    def __init__(self, root):
        self.root = root

        # the app window will be on top of other windows
        self.root.wm_attributes("-topmost", 1)

        self.button = tk.Button(master=self.root, text="Crop", command=self.activate_cropping)
        self.button.pack(fill=tk.BOTH, expand=False)

        # the program terminates when pressing ESC
        # we need to fix this
        self.root.bind("<Escape>", lambda event: self.delete_canvas())

        self.root.bind("q", lambda event: self.root.quit())

        self.root.bind("y", self.y_handler)

    def delete_canvas(self):
        del self.canvas

    def activate_cropping(self, event=None):
        # hide the crop button
        self.button.pack_forget()

        # Capture the full screen to be displayed for cropping
        self.full_screen_image = ImageGrab.grab()
        self.full_screen_image.save("initial_full_screen_image.png")

        self.root.attributes("-fullscreen", True)

        # resize image
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        screenshot = self.full_screen_image.resize((screen_width, screen_height))

        self.canvas = tk.Canvas(master=self.root, cursor="cross")
        

        photo = ImageTk.PhotoImage(screenshot)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # bind events
        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)

        # initiate selection region
        self.selection = None

    def start_selection(self, event):
        self.canvas.delete("selection")
        self.selection = None
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

    def update_selection(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        if self.selection:
            self.canvas.coords(self.selection, self.start_x, self.start_y, cur_x, cur_y)
        else:
            self.selection = self.canvas.create_rectangle(self.start_x, self.start_y, cur_x, cur_y, outline="red", tags="selection")

    def end_selection(self, event=None):
        pass

    def handle_selected_region(self, event):
        if self.selection: # if the selected region exists
            selection_coords = self.canvas.coords(self.selection)
            bbox = self.get_corrected_coordinates(selection_coords)
            cropped_image = self.full_screen_image.crop(bbox)

            # save the cropped image
            saved_image_path = os.path.join("images", "captured_screen.png")
            cropped_image.save(saved_image_path)

            # call ocr API
            api_url = 'http://127.0.0.1:8503/predict-from-image'
            headers = {
                'accept': 'application/json',
            }
            files = {
                'file': ('captured_screen.png', open(saved_image_path, 'rb'), 'image/png'),
            }
            response = requests.post(api_url, headers=headers, files=files) # add await?
            # this is blocking the code... nothing else can be done before this line is done
            # this line takes 16 seconds
            print("Here is the transformed region in markdown text:")
            print(response.text)


    def get_corrected_coordinates(self, coord: list[float]):
        '''
        coord: the original coordinates of the selected region self.selection
        We need this because the canvas has width and height (1536, 864) for me, whereas
        the full screen image has width and height (1920, 1080).
        Hence, we need to rescale the coordinates.
        '''
        x1, y1, x2, y2 = coord
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        full_image_width, full_image_height = self.full_screen_image.size
        x_ratio = full_image_width / canvas_width
        y_ratio = full_image_height / canvas_height

        # for testing
        #print(f"Here is the bbox of canvas: {(canvas_width, canvas_height)}")
        #print(f"Here is the bbox of image: {(full_image_width, full_image_height)}")

        return (int(x1*x_ratio), int(y1*y_ratio), int(x2*x_ratio), int(y2*y_ratio))

    def to_initial_mode(self):
        self.root.attributes("-fullscreen", False)
        self.canvas.pack_forget()
        self.button.pack(fill=tk.BOTH, expand=False)

    def y_handler(self, event):
        # handles events after pressing y key
        self.handle_selected_region(event)
        self.to_initial_mode()
    

if __name__ == '__main__':
    # loads OCR model
    load_model()    

    # start tkinter screen capture app
    root = tk.Tk()
    app = ScreenCaptureApp(root)
    root.mainloop()

