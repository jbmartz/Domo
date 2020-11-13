# CloudNotes: a command line application to create small text
#  files on a user's Google Drive using Drive API v3

from cmd import Cmd
import google_drive
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tkinter import *

# scope requested during OAuth2.0 authorization
#  see https://developers.google.com/identity/protocols/oauth2/scopes#drive
#  the following scope allows an application to access all files/folders
#    created by the application
SCOPES = ['https://www.googleapis.com/auth/drive.file']


class CloudNotes(Cmd):
    prompt = "\033[91m(CloudNotes) \033[0m"    # prompt on shell
    cwd = None                  # current working directory id and name
    cwd_list = dict()           # internal dictionary to store metadata of contents in current working directory
    pass

    # Constructor
    def __init__(self):
        super(CloudNotes, self).__init__()
        self.GD = None

    # Start function called to start the application
    def start(self):
        token = self.try_oauth()    # try to get access token
        if token is None:
            print("CloudNotes initialization failed!")
            return

        # initialize Google Drive API v3 with token
        self.GD = google_drive.GoogleDriveAPI(token)

        # check/create CloudNotes root directory
        self.load_cloudnotes_directory()
        if self.cwd is None:
            print("CloudNotes initialization failed!")
            return

        # load CloudNotes root directory
        self.load_directory(self.cwd["id"])

        # start shell with welcome message
        self.cmdloop("\033[94m\033[1mWelcome to CloudNotes!\033[0m\n"
                     "A command line utility to store text notes in Google Drive")

    # Load the CloudNotes root directory information
    def load_cloudnotes_directory(self):
        # retrieve list of files and folders in user's drive
        response = self.GD.gd_list()
        if response is None:
            return

        # find CloudNotes_Root directory
        for f in response:
            if f.get("mimeType", None) == "application/vnd.google-apps.folder" and f["name"] == "CloudNotes_Root":
                self.cwd = {"id": f["id"], "name": "CloudNotes_Root"}
                return

        # not found; create one
        print("Unable to find a CloudNotes_Root directory...creating one")
        response = self.GD.gd_create_directory(name="CloudNotes_Root")
        if response is None:
            return

        # store id and name of current working directory
        self.cwd = {"id": response["id"], "name": response["name"]}

    # Load the list of files/directories in a given directory
    def load_directory(self, dir_id):
        # no directory id given
        if dir_id is None:
            return

        # get content of directory using id
        response = self.GD.gd_list(dir_id=dir_id)
        if response is None:
            return

        # store in application's dictionary
        self.cwd_list.clear()
        for f in response:
            if f.get("mimeType", None) == "application/vnd.google-apps.folder":     # a directory
                f_type = "folder"
            else:
                f_type = "file"

            # populate dictionary using name as key, and object's id and type
            #   as value (another dictionary)
            self.cwd_list[f["name"]] = {"id": f["id"], "type": f_type}

    # Run command to list files/directories in current working directory
    def do_list(self, inp):
        # refresh contents in internal dictionary
        self.load_directory(self.cwd["id"])

        # print each object in dictionary
        for f in self.cwd_list:
            if self.cwd_list[f]["type"] == "folder":    # directories shown in bold color
                print("\033[36m\033[1m"+f+"\033[0m")
            else:
                print(f)

    # Run command to print current working directory
    def do_cwd(self, inp):
        print("Current working directory: \033[36m\033[1m" + self.cwd["name"] + "\033[0m")

    # Run command to exit the application
    def do_exit(self, inp):
        print("Bye\n")
        return True

    # Run command to change directory
    def do_cd(self, inp):
        # input name must be in current directory
        if inp not in self.cwd_list:
            print("*** Error: No such directory")
            return

        # set new current directory data and refresh contents in internal dictionary
        self.cwd["id"] = self.cwd_list[inp]["id"]
        self.cwd["name"] = inp
        self.load_directory(self.cwd["id"])

    # Run command to go up one directory
    def do_up(self, inp):
        # cannot go past CloudNotes root directory
        if self.cwd["name"] == "CloudNotes_Root":
            print("You are already at the CloudNotes root directory")
            return

        # get parent directory's id
        response = self.GD.gd_get_metadata(res_id=self.cwd["id"])
        if response is None:
            return
        parent_id = response["parents"][0]

        # get parent directory's name
        response = self.GD.gd_get_metadata(res_id=parent_id)
        if response is None:
            return
        parent_name = response["name"]

        # set new current directory data and refresh contents in internal dictionary
        self.cwd["id"] = parent_id
        self.cwd["name"] = parent_name
        self.load_directory(self.cwd["id"])

    # Run command to create a directory
    def do_mkdir(self, inp):
        # cannot have duplicate name
        if inp in self.cwd_list:
            print("*** Error: Name already exists in current directory")
            return

        # cannot use CloudNotes_Root as name
        if inp == "CloudNotes_Root":
            print("The name CloudNotes_Root is reserved for use in the application. Please use a different name.")
            return

        # call API to create the directory in the current working directory
        response = self.GD.gd_create_directory(name=inp, parent_id=self.cwd["id"])
        if response is None:
            return

        # refresh contents in internal dictionary
        self.load_directory(self.cwd["id"])

    # Run command to create a note
    def do_create(self, inp):
        # cannot have duplicate name
        if inp in self.cwd_list:
            print("*** Error: Name already exists in current directory")
            return

        # cannot use CloudNotes_Root as name
        if inp == "CloudNotes_Root":
            print("The name CloudNotes_Root is reserved for use in the application. Please use a different name.")
            return

        # open the notepad and get contents
        note = self.show_notepad()

        # save after confirmation prompt
        choice = input("Save note? [y/n] ")
        if choice.lower() in ("y", "yes"):
            # call API to create file in current working directory
            response = self.GD.gd_create_text_file(name=inp, parent_id=self.cwd["id"], contents=note)
            if response is None:
                return
            # refresh contents in internal dictionary
            self.load_directory(self.cwd["id"])
        else:
            return

    # Run command to display a note's contents
    def do_show(self, inp):
        # input name must exist in current directory
        if inp not in self.cwd_list:
            print("*** Error: No such file")
            return

        # input name cannot be of a directory
        if self.cwd_list[inp]["type"] == "folder":
            print("*** Error: " + inp + " is a directory")
            return

        # call API to get file's contents and display
        response = self.GD.gd_export_text_file(file_id=self.cwd_list[inp]["id"])
        if response is None:
            return
        print(response[3:])     # ignoring BOM

    # Run command to edit a note's contents
    def do_edit(self, inp):
        # input name must exist in current directory
        if inp not in self.cwd_list:
            print("*** Error: No such file")
            return

        # input name cannot be of a directory
        if self.cwd_list[inp]["type"] == "folder":
            print("*** Error: " + inp + " is a directory")
            return

        # call API to retrieve the file's current contents
        response = self.GD.gd_export_text_file(self.cwd_list[inp]["id"])
        if response is None:
            return

        # open the notepad pre-populated with retrieved contents
        note = self.show_notepad(contents=response[3:])

        # save after confirmation prompt
        choice = input("Save note? [y/n] ")
        if choice.lower() in ("y", "yes"):
            # call API to update file's contents
            response = self.GD.gd_update_text_file(file_id=self.cwd_list[inp]["id"], contents=note)
            if response is None:
                return
        else:
            return

    # Run command to delete a file/directory
    def do_delete(self, inp):
        # input name must exist in current directory
        if inp not in self.cwd_list:
            print("*** Error: No such file or directory")
            return

        # show warning prompt before deleting a directory
        if self.cwd_list[inp]["type"] == "folder":
            choice = input("\033[36m\033[1m" + inp + "\033[0m is a directory. "
                                                     "All contents inside it will be deleted. Proceed? [y/n] ")
            if choice.lower() not in ("y", "yes"):
                return

        # call API to delete file/directory
        response = self.GD.gd_delete(res_id=self.cwd_list[inp]["id"])
        if response is None:
            return

        # remove entry from internal dictionary
        del self.cwd_list[inp]

    """Help messages for the commands"""
    def help_create(self):
        print("Create a note file in the current directory.")
        print("Syntax: create [file name]")

    def help_cd(self):
        print("Change into a directory present in the current directory.")
        print("Syntax: cd [directory name]")

    def help_cwd(self):
        print("Print name of current directory.")
        print("Syntax: cwd")

    def help_delete(self):
        print("Delete a directory from the current directory.")
        print("Syntax: delete [directory name]")

    def help_edit(self):
        print("Edit a note file in the current directory.")
        print("Syntax: edit [file name]")

    def help_exit(self):
        print("Exit application.")
        print("Syntax: exit")

    def help_list(self):
        print("Show contents of current directory. Sub-directories are shown as colored and bold names.")
        print("Syntax: list")

    def help_mkdir(self):
        print("Create a directory in the current directory.")
        print("Syntax: mkdir [directory name]")

    def help_show(self):
        print("Show contents of a note file in the current directory.")
        print("Syntax: show [file name]")

    def help_up(self):
        print("Move a level up in the directory structure.")
        print("Syntax: up")

    # Ctrl+D handlers (same as exit command)
    do_EOF = do_exit
    help_EOF = help_exit

    # Notepad GUI
    def show_notepad(self, contents=None):
        root = Tk()
        root.geometry("350x250")
        root.title("CloudNotes Notepad")
        root.minsize(height=250, width=350)
        root.maxsize(height=250, width=350)

        # add scrollbar
        scrollbar = Scrollbar(root)
        scrollbar.pack(side=RIGHT, fill=Y)

        # initialize note storage
        note = StringVar()
        if contents is not None:    # pre-populate if contents are provided
            note.set("\n".join(contents.splitlines()))

        # create a Text widget
        text_info = Text(root, yscrollcommand=scrollbar.set)
        text_info.insert(END, note.get())
        text_info.pack(fill=BOTH)
        scrollbar.config(command=text_info.yview)

        # define close window handler
        def on_closing():
            # get the entered text
            note.set(text_info.get("1.0", "end-1c"))
            root.destroy()
        root.protocol("WM_DELETE_WINDOW", on_closing)

        # start notepad (waits here until GUI is closed)
        root.mainloop()

        # return the notepad's contents
        return note.get()

    # Get user authorization and access token
    def try_oauth(self):
        creds = None

        if not os.path.exists("credentials.json"):
            print("Error: Missing credentials.json file")
            return None

        try:
            # file token.pickle stores the user's access and refresh tokens, and is
            #   created automatically when the authorization flow completes for
            #   the first time
            if os.path.exists("token.pickle"):
                with open("token.pickle", "rb") as token:
                    creds = pickle.load(token)

            # run OAuth2.0 flow if there are no valid credentials about the user
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    print("Trying token refresh")
                    creds.refresh(Request())    # refresh token grant
                else:   # authorization code grant
                    print("Trying OAuth2.0 authorization")
                    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                    creds = flow.run_local_server(port=0)

                # save the credentials for the next run
                with open("token.pickle", "wb") as token:
                    pickle.dump(creds, token)

                print("Authorization obtained")
            else:
                print("Using tokens from storage")

            if creds is not None:
                return creds.token  # the access token
            else:
                return None     # no access token

        except pickle.PickleError as e:
            print("Pickle error: "+str(e))
            print("Delete token.pickle and retry")
            return None
        except Exception as e:
            print("Error: " + str(e))
            return None     # no access token
