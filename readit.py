import boto3
import botocore.exceptions
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import Entry, Label, StringVar, Canvas, PhotoImage, filedialog, OptionMenu
from PyPDF2 import PdfFileReader
from tkinter.simpledialog import askstring
import re


class ReadIt:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("Read it to me")
        self.root.config(padx=25, pady=50, bg="white")

        Label(text="PDF to Audio.", bg='white', font=("Calibri", 12, "bold")).grid(row=0, column=0, columnspan=2)
        Label(text="Drag and Drop PDF to the box below and choose where to save", bg='white',
              font=("Calibri", 10)).grid(row=1, column=0, pady=7, columnspan=2)

        # get the keys
        Label(text="AWS AccessKey Id", bg='white',
              font=("Calibri", 11, "bold")).grid(row=2, column=0, pady=2)
        self.access_key = Entry(self.root, width=25)
        self.access_key.grid(row=3, column=0, pady=2)
        Label(text="AWS SecretKey", bg='white',
              font=("Calibri", 11, "bold")).grid(row=2, column=1, pady=2)

        self.secret_key = Entry(self.root, width=25)
        self.secret_key.grid(row=3, column=1, pady=2)

        # voice actor options
        Label(text="Voice Choices", bg='white',
              font=("Calibri", 11, "bold")).grid(row=4, column=1, pady=2)
        options_list = ["Joanna", "Salli", "Kimberly", "Kendara", "Ivy", "Kevin", "Matthew", "Justin", "Joey"]
        self.option_sv = StringVar()
        self.option_sv.set("Matthew")
        self.options = OptionMenu(self.root, self.option_sv, *options_list)
        self.options.grid(row=5, column=1, pady=2, sticky=["e", "w"])
        # canvas to put things in
        self.canvas = Canvas(width=300, height=200, bg="white")
        self.canvas.grid(row=6, column=0, columnspan=2, pady=5)

        # pdf img background
        self.pdf_img_red = PhotoImage(file="./assets/pdf_logo.png")
        self.pdf_img_red = self.pdf_img_red.subsample(3)
        self.pdf_img_blue = PhotoImage(file="./assets/pdf_logo_blue.png")
        self.pdf_img_blue = self.pdf_img_blue.subsample(3)
        self.canvas_bg = self.canvas.create_image(150, 100, image=self.pdf_img_red, tag="not-submitted")
        # Drag and Drop box using Canvas field
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self.pdf_render)

        self.warning_label = Label(text="", bg="white", fg='red', font=("Calibri", 10))
        self.warning_label.grid(row=7, column=0, pady=5, columnspan=2)
        # Create confirm button

    def pdf_render(self, e):
        if self.access_key.get() != "" and self.secret_key.get() != "":
            pdf_route = re.sub("[{}]", "", e.data)
            pdf_status = self.canvas.itemcget(self.canvas_bg, "tag")
            if pdf_route.endswith(".pdf") and pdf_status == "not-submitted":
                self.canvas.itemconfig(self.canvas_bg, image=self.pdf_img_blue, tag="submitted")
                self.warning_label.config(text="")
                with open(pdf_route, "rb") as pdf:
                    pdf_data = PdfFileReader(pdf, strict=False)
                    file_title = pdf_data.getDocumentInfo().title
                    full_text = ""
                    for i in range(PdfFileReader(pdf, strict=False).numPages):
                        full_text += pdf_data.getPage(i).extractText()

                # # check if path is selected
                if len(full_text) < 3000:
                    save_path = filedialog.askdirectory()
                    if save_path == "":
                        self.warning_label.config(text="Please choose correct directory!",
                                                  fg="red")
                        self.canvas.itemconfig(self.canvas_bg, image=self.pdf_img_red, tag="submitted")
                    else:
                        self.pdf_to_speech(text=full_text, large=False, title=file_title,
                                           path=save_path)
                else:
                    bucket = askstring('AWS Bucket Name Required',
                                       f'There are {len(full_text)} Characters.\nPlease enter your AWS Bucket name\nand press "Ok" to continue')
                    if bucket:
                        self.warning_label.config(text="Processing",
                                                  fg="blue")
                        self.pdf_to_speech(text=full_text, large=True, title=file_title, bucket=bucket)
                    else:
                        self.warning_label.config(text="Provide another file to continue",
                                                  fg="red")
            else:
                self.warning_label.config(text="Please provide pdf file", fg="red")
        else:
            if self.canvas.itemcget(self.canvas_bg, "tag") == "submitted":
                self.warning_label.config(text="Please wait until files rendered", fg="red")
            else:
                self.warning_label.config(text="Please provide AWS Access Key and Secret Key!", fg="red")

    def pdf_to_speech(self, text: str, large: bool, title: str, **kwargs):
        """Using AWS Polly to convert pdf text to mp3"""
        polly_client = boto3.Session(
            aws_access_key_id=self.access_key.get(),
            aws_secret_access_key=self.secret_key.get(),
            region_name="us-east-1").client('polly')
        try:
            file_title = title.replace(" ", "-")
        except AttributeError:
            file_title = "Undefined"
        if large:
            polly_client.start_speech_synthesis_task(VoiceId=self.option_sv.get(),
                                                     OutputS3BucketName=kwargs.get('bucket', None).replace("_", "-"),
                                                     OutputS3KeyPrefix=file_title,
                                                     OutputFormat="mp3",
                                                     Text=text,
                                                     Engine="neural")
            try:
                pass
            except botocore.exceptions.ClientError:
                self.warning_label.config(text="Incorrect AWS Account Id or Secret Key", fg="red")
            else:
                self.warning_label.config(text="Please Check your AWS Bucket!", fg="blue")
        else:
            try:
                res = polly_client.synthesize_speech(VoiceId=self.option_sv.get(),
                                                     OutputFormat='mp3',
                                                     Text=text,
                                                     Engine='neural')
            except botocore.exceptions.ClientError:
                self.warning_label.config(text="Incorrect AWS Account Id or Secret Key")
            else:
                file = open(f"{kwargs.get('path', None)}/{file_title}.mp3", "wb")
                file.write(res["AudioStream"].read())
                file.close
                self.warning_label.config(text="Processed", fg="blue")

        self.canvas.itemconfig(self.canvas_bg, image=self.pdf_img_red, tag="not-submitted")
