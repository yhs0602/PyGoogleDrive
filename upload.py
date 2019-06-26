from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import sys
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']
# Call the Drive v3 API
class DriveHelper:
    def __init__(self, refresh):
        """Shows basic usage of the Drive v3 API.
        Prints the names and ids of the first 10 files the user has access to.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle') and not refresh:
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('drive', 'v3', credentials=creds)

    def exists(self, filename, isfolder = False):
        filename = self.escapename(filename)
        results = self.service.files().list(
            pageSize = 1, q =("name='" + filename+"'") +("and mimeType='application/vnd.google-apps.folder'" if isfolder else "")
        ).execute()
        items = results.get('files',[])
        if not items:
            return False
        return True
    
    def getID(self, filename, parentID = None ):
        filename = self.escapename(filename)
        results = self.service.files().list(
            pageSize = 1, fields = "files(id)", q =("name='" + filename +"'") + ("and '"+parentID+"' in parents" if parentID else "")
        ).execute()
        items= results.get('files',[])
        if not items:
            return None
        else:
            return items[0]['id']
       
    def getName(self, id):
        results = self.service.files().list(
            pageSize = 1, fields = "files(name)", q ="id='" + id +"'"
        ).execute()
        items= results.get('files',[])
        if not items:
            return None
        else:
            return items[0]['name']
       

    # name id
    def existsInNI(self, filename, folderId):
        filename = self.escapename(filename)
        results = self.service.files().list(
            pageSize = 1, q =("name='" + filename+"'") + ("and '" + str(folderId) +"' in parents" if folderId else "")
        ).execute()
        items = results.get('files',[])
        if not items:
            return False
        return True

    @staticmethod
    def escapename(name):
        s = ""
        for c in name:
            if c == "'":
                s+='\\'
            s+=c
        return s
    
    def createFolder(self, folderName, parentID = None):
        # Create a folder on Drive, returns the newely created folders ID
        body = {
          'name': folderName,
          'mimeType': "application/vnd.google-apps.folder"
        }
        if parentID:
            print("PARENT ID:",parentID)
            body['parents'] = [ parentID]
        root_folder = self.service.files().create( body = body).execute()
        print("Created folder id:", root_folder['id'])
        return root_folder['id']

    # uploads a single file
    def uploadFile(self, fromfile, filename, parentid = None, overwrite = False):
        if not overwrite:
            if self.existsInNI(filename,parentid) and not self.existsInTrash(filename, parentid):
                print("Warning:File alerady exists:",filename,"SKIPPING")
                return
        print("Uploading file ", filename)
        file_metadata = {'name': filename}
        if parentid:
            file_metadata['parents'] =  [parentid]
        media = MediaFileUpload(fromfile)#,
                        #mimetype='application/vnd.google-apps.file')
        file = self.service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
        return file.get('id')

    # upload folder without dup recursively
    def uploadFolderWithoutDupI(self, fromroot, toroot, overwrite = False):
        files = os.listdir(fromroot)
        #folderid = toroot
        #folderid = self.getID(toroot)
        for file in files:
            if os.path.isdir(os.path.join(fromroot,file)):
                if not self.existsInNI(file,toroot) or self.existsInTrash(file,toroot):
                    folderid = self.createFolder(file,toroot)
                else:
                    folderid = self.getID(file,toroot)
                self.uploadFolderWithoutDupI(os.path.join(fromroot, file),folderid,overwrite)
            else:
                fullpath = os.path.join(fromroot, file)
                self.uploadFile(fullpath, file, toroot, overwrite)
    
    #, fields="files(id, name,labels)"
    # fields="labels"
    def existsInTrash(self, filename, parentid):
        filename = self.escapename(filename)
        results = self.service.files().list(
            pageSize = 1, q =("name='" + filename+"'") + ("and '" + str(parentid) +"' in parents" if parentid else "")
        ).execute()
        #print(results)
        items = results.get('files',[])
        if not items:
            return False
        #print(items)
        id = items[0]['id']
        results = self.service.files().get(fileId = id, fields = 'trashed').execute()
        #print(results)
        return results['trashed']

    def removeFile(self, file_id):
        """Permanently delete a file, skipping the trash.

          Args:
            service: Drive API service instance.
            file_id: ID of the file to delete.
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
        except: # error:  #'''errors.HttpError,'''
            print ('An error occurred:%s'% sys.exc_info()[0])

    def ls(self, folderid):
        nextPageToken = None
        while True:
            results = self.service.files().list(
                pageSize=10, pageToken = nextPageToken, fields="nextPageToken, files(id, name)", q="'"+str(folderid) +"' in parents").execute()
            items = results.get('files', [])
            nextPageToken = results.get('nextPageToken')
            if not items:
                print('No files found.')
            else:
                print('Files:')
                for item in items:
                    print(u'{0} ({1})'.format(item['name'], item['id']))
            if not nextPageToken:
                break

def main():
    refresh = False
    if len(sys.argv) >1:
        if sys.argv[1] == 'refresh':
            refresh = True
    helper = DriveHelper(refresh)
    #filename = input("enter file name to check:")
    #bexists = helper.exists(filename)
    #if bexists:
    #    print("Exists")
    #else:
    #    print("Not Exists")
    folderid = helper.getID('Songs') # items[0]['id']
    #helper.ls(folderid)
    #folderid = helper.getID('hw')
    helper.uploadFolderWithoutDupI('0624',folderid)
    #fid = helper.uploadFile('BeatmapCreator.py','BeatmapCreator')
    #input("Delete?")
    #helper.removeFile(fid)
if __name__ == '__main__':
    main()
