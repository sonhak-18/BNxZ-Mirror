#!/usr/bin/env python3
from logging import getLogger
from urllib.parse import quote as rquote

from bot import list_drives_dict, config_dict
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.mirror_utils.gdrive_utils.helper import GoogleDriveHelper

LOGGER = getLogger(__name__)


class gdSearch(GoogleDriveHelper):

    def __init__(self, stopDup=False, noMulti=False, isRecursive=True, itemType=''):
        super().__init__()
        self.__stopDup = stopDup
        self.__noMulti = noMulti
        self.__isRecursive = isRecursive
        self.__itemType = itemType

    def __drive_query(self, dirId, fileName, isRecursive):
        try:
            if isRecursive:
                if self.__stopDup:
                    query = f"name = '{fileName}' and "
                else:
                    fileName = fileName.split()
                    query = "".join(
                        f"name contains '{name}' and "
                        for name in fileName
                        if name != ""
                    )
                    if self.__itemType == "files":
                        query += f"mimeType != '{self.G_DRIVE_DIR_MIME_TYPE}' and "
                    elif self.__itemType == "folders":
                        query += f"mimeType = '{self.G_DRIVE_DIR_MIME_TYPE}' and "
                query += "trashed = false"
                if dirId == "root":
                    return (
                        self.service.files()
                        .list(
                            q=f"{query} and 'me' in owners",
                            pageSize=200,
                            spaces="drive",
                            fields="files(id, name, mimeType, size, parents)",
                            orderBy="folder, name asc",
                        )
                        .execute()
                    )
                else:
                    return (
                        self.service.files()
                        .list(
                            supportsAllDrives=True,
                            includeItemsFromAllDrives=True,
                            driveId=dirId,
                            q=query,
                            spaces="drive",
                            pageSize=150,
                            fields="files(id, name, mimeType, size, teamDriveId, parents)",
                            corpora="drive",
                            orderBy="folder, name asc",
                        )
                        .execute()
                    )
            else:
                if self.__stopDup:
                    query = f"'{dirId}' in parents and name = '{fileName}' and "
                else:
                    query = f"'{dirId}' in parents and "
                    fileName = fileName.split()
                    for name in fileName:
                        if name != "":
                            query += f"name contains '{name}' and "
                    if self.__itemType == "files":
                        query += f"mimeType != '{self.G_DRIVE_DIR_MIME_TYPE}' and "
                    elif self.__itemType == "folders":
                        query += f"mimeType = '{self.G_DRIVE_DIR_MIME_TYPE}' and "
                query += "trashed = false"
                return (
                    self.service.files()
                    .list(
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        q=query,
                        spaces="drive",
                        pageSize=150,
                        fields="files(id, name, mimeType, size)",
                        orderBy="folder, name asc",
                    )
                    .execute()
                )
        except Exception as err:
            err = str(err).replace(">", "").replace("<", "")
            LOGGER.error(err)
            return {"files": []}

    def drive_list(self, fileName, isRecursive=None, itemType=''):
        msg = ""
        fileName = self.escapes(str(fileName))
        contents_no = 0
        telegraph_content = []
        Title = False
        self.service = self.authorize()
        if len(list_drives_dict) > 1:
            if not self.alt_auth and self.use_sa:
                self.alt_auth = True
                self.use_sa = False
        for drive_name, drive_dict in list_drives_dict.items():
            dir_id = drive_dict['drive_id']
            index_url = drive_dict['index_link']
            isRecur = False if self.__isRecursive and len(dir_id) > 23 else self.__isRecursive
            response = self.__drive_query(dir_id, fileName, isRecur)
            if not response["files"]:
                if self.__noMulti:
                    break
                else:
                    continue
            if not Title:
                msg += f'<h4>Search Result For {fileName}</h4>'
                Title = True
            if drive_name:
                msg += f"<br>❏ <b>{drive_name}</b><br>"
            for file in response.get('files', []):
                mime_type = file.get('mimeType')
                if mime_type == "application/vnd.google-apps.folder":
                    furl = f"https://drive.google.com/drive/folders/{file.get('id')}"
                    msg += f"🗂 <b>{file.get('name')}<br>(folder)</b><br>"
                    if not config_dict['DISABLE_DRIVE_LINK']:
                        msg += f"<b><a href={furl}>☁️ Drive Link</a></b> | "
                    if index_url:
                        if isRecur:
                            url_path = "/".join(rquote(n, safe='')
                                                for n in self.__get_recursive_list(file, dir_id))
                        else:
                            url_path = rquote(f'{file.get("name")}', safe='')
                        url = f'{index_url}/{url_path}/'
                        msg += f'<b><a href="{url}">⚡️ Index Link</a></b>'
                elif mime_type == 'application/vnd.google-apps.shortcut':
                    furl = f"https://drive.google.com/drive/folders/{file.get('id')}"
                    msg += f"⁍<a href='https://drive.google.com/drive/folders/{file.get('id')}'>{file.get('name')}" \
                        f"</a> (shortcut)"
                else:
                    furl = f"https://drive.google.com/uc?id={file.get('id')}&export=download"
                    msg += f"📁 <b>{file.get('name')}<br>({get_readable_file_size(int(file.get('size', 0)))})</b><br>"
                    if not config_dict['DISABLE_DRIVE_LINK']:
                        msg += f"<b><a href={furl}>☁️ Drive Link</a></b> | "
                    if index_url:
                        if isRecur:
                            url_path = "/".join(rquote(n, safe='')
                                                for n in self.__get_recursive_list(file, dir_id))
                        else:
                            url_path = rquote(f'{file.get("name")}', safe='')
                        url = f'{index_url}/{url_path}/'
                        msg += f'<b><a href="{url}">⚡️ Index Link</a></b>'
                        if mime_type.startswith(('image', 'video', 'audio')):
                            urlv = f'{index_url}/{url_path}&view=true'
                            msg += f' | <b><a href="{urlv}">View Link</a></b>'
                msg += '<br><br>'
                contents_no += 1
                if len(msg.encode('utf-8')) > 39000:
                    telegraph_content.append(msg)
                    msg = ''
            if self.__noMulti:
                break

        if msg != '':
            telegraph_content.append(msg)
        return telegraph_content, contents_no
