# Google Drive v3 Files API requests
import requests
import json

# Base URIs for Drive v3 API requests
GD_UPLOAD_BASE_URI = "https://www.googleapis.com/upload/drive/v3/files/"
GD_METADATA_BASE_URI = "https://www.googleapis.com/drive/v3/files/"


class GoogleDriveAPI:
    token = None  # the access token to use in requests

    # Constructor
    def __init__(self, token):
        super().__init__()
        self.token = token

    # Make an API endpoint request (https://requests.readthedocs.io/en/latest/api/)
    #   Input: method = request method (GET, POST, PATCH, etc.) as a string
    #          url = request url as a string
    #          url_params = dictionary of url parameters
    #          headers = dictionary of additional headers to include in the request
    #          body = request body as a string
    #   Return: a tuple of status code and response (or error) message
    #           when returned status code is 9999, the error message is
    #           an exception message
    #
    def make_request(self, method, url, url_params=dict(),
                     headers=dict(), body=None):
        # add Authorization header
        headers["Authorization"] = "Bearer " + self.token  # bearer authentication

        # make the request
        try:
            r = requests.request(method, url, headers=headers, params=url_params, data=body)
        except Exception as e:
            return 9999, str(e)

        # get the body of the response as text
        # NOTE: if the text is in json format, it can be converted to
        #       a dictionary using json.loads()
        body = r.text

        # return value contains the error message or the body
        if r.status_code > 299:
            res_dict = json.loads(body)
            ret_val = res_dict["error"]["message"]
        else:
            ret_val = body

        return r.status_code, ret_val

    # TODO: List contents of a given directory (Files:list endpoint)
    #   Input: dir_id = id of directory to list
    #                   None means user's Google Drive root directory
    #   Return: None on error, otherwise
    #           an array of dictionary objects
    #           representing the files[] list (see Drive API documentation)
    #   (ignore nextPageToken in this assignment)
    # Note: Google will not show files that are not created by the application
    #
    def gd_list(self, dir_id=None):
        # "application/vnd.google-apps.folder"

        if dir_id is None:
            ret_val = GoogleDriveAPI.make_request(self, method="GET", url=GD_METADATA_BASE_URI)

            if ret_val[0] != 200:
                return None

            files = [json.loads(ret_val[1])]
            return files
        else:

            url_params = {
                "fields": "*",
                "spaces": "drive",
                "q": "parents in '{}'".format(dir_id)
            }

            ret_val = GoogleDriveAPI.make_request(self, method="GET", url=GD_METADATA_BASE_URI, url_params=url_params)

            if ret_val[0] != 200:
                return None

            files = [json.loads(ret_val[1])]

            return files[0]['files']

    # TODO: Retrieve metadata about an object (Files:get endpoint)
    #   Input: res_id = id of an object (file/directory)
    #   Return: None on error, otherwise
    #           a dictionary containing the id, name and parents list
    #
    def gd_get_metadata(self, res_id):

        if res_id is None:
            return None

        ret_val = GoogleDriveAPI.make_request(self, method="GET", url=GD_METADATA_BASE_URI + res_id,
                                              url_params={"fields": "id,name,parents"})
        if ret_val[0] != 200:
            return None

        files = [json.loads(ret_val[1])]

        return files[0]

    # TODO: Create a directory in a given directory (Files:create metadata uri endpoint)
    #   Input: name = name of directory to create
    #          parent_id = id of directory under which the new
    #                      directory is to be created
    #                      None means user's Google Drive root directory
    #   Return: None on error, otherwise
    #           a dictionary containing the id and name of the created directory
    #
    def gd_create_directory(self, name, parent_id=None):
        if name is None:
            return None

        if parent_id is None:
            body = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
        else:
            body = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }

        ret_val = GoogleDriveAPI.make_request(self, method="POST", url=GD_METADATA_BASE_URI, headers={'Content-type': 'application/json'}, body=json.dumps(body))
        if ret_val[0] != 200:
            return None

        ret_dict = json.loads(ret_val[1])
        return ret_dict

    # TODO: Create a new file with text data in a given directory (Files:create upload uri endpoint)
    #   Input: name = name of the text file to create
    #          parent_id = id of directory under which the new
    #                      file is to be created
    #          contents = content to put in the file
    #   Return: None on error, otherwise
    #           a dictionary containing the id and name of the created file
    #
    def gd_create_text_file(self, name, parent_id, contents):
        if name is None or parent_id is None or contents is None:
            return None
        headers = {'Content-Type': 'multipart/related; boundary=boundary'}
        boundary = '--boundary';
        meta_data = {
            "parents": [parent_id],
            "name": name,
            'mimeType': 'application/vnd.google-apps.file'
        }

        multi_part_request_body = boundary + "\nContent-Type: text/plain\n\n" + contents + "\n" + boundary + "--"
        concat = boundary + "\nContent-Type: application/json; charset=UTF-8\n\n" + json.dumps(
            meta_data) + "\n" + multi_part_request_body
        ret_val = GoogleDriveAPI.make_request(self, method="POST", url=GD_UPLOAD_BASE_URI, headers=headers,
                                              url_params={"uploadType": "multipart"}, body=concat)

        return json.loads(ret_val[1])

    # TODO: Update text data in an existing file (Files:update upload uri endpoint)
    #   Input: file_id = id of file to update
    #          contents = new content to replace in the file
    #   Return: None on error, otherwise
    #           a dictionary containing the id and name of the updated file
    #
    def gd_update_text_file(self, file_id, contents):

        if file_id is None or contents is None:
            return None

        ret_val = GoogleDriveAPI.make_request(self, method="PATCH", url=GD_UPLOAD_BASE_URI + file_id, headers={"Content-Type": "text/plain"},
                                              url_params={"uploadType": "media"}, body=contents)

        if ret_val[0] != 200:
            return None

        return ret_val[1]


    # TODO: Export/download text contents of a file (Files:export endpoint)
    #   Input: file_id = id of file to download
    #   Return: None on error, otherwise
    #           a string containing the downloaded content
    #
    # NOTE: Set mime type as text/plain when downloading text file
    def gd_export_text_file(self, file_id):
        if file_id is None:
            return None

        ret_val = GoogleDriveAPI.make_request(self, method="GET", url=GD_METADATA_BASE_URI + file_id + "/export", url_params={
            "mimeType": "text/plain"})

        if ret_val[0] != 200:
            return None

        return ret_val[1]

    # TODO: Delete a file/directory (Files:delete endpoint)
    #   Input: res_id = id of file or directory to delete
    #   Return: None on error, otherwise
    #           an empty string
    #
    def gd_delete(self, res_id):
        ret_val = GoogleDriveAPI.make_request(self, method="DELETE", url=GD_METADATA_BASE_URI + res_id)

        if ret_val[0] != 204:
            return None

        return ""
