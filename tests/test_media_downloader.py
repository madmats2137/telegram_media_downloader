"""Unittest module for media downloader."""
import asyncio
import copy
import os
import platform
import unittest
from datetime import datetime

import mock
import pyrogram

from media_downloader import (
    DOWNLOADED_IDS,
    _get_media_meta,
    _can_download,
    _get_media_meta,
    _is_exist,
    begin_import,
    download_media,
    main,
    process_messages,
    update_config,
)

MOCK_DIR: str = "/root/project"
if platform.system() == "Windows":
    MOCK_DIR = "\\root\\project"
MOCK_CONF = {
    "api_id": 123,
    "api_hash": "hasw5Tgawsuj67",
    "chats": [
        {
            "id": 8654123,
            "last_read_message_id": 0,
            "ids_to_retry": [1],
        }
    ],
    "chat_names": {"8654123": "Custom Channel Name"},
    "media_types": ["audio", "voice"],
    "file_formats": {"audio": ["all"], "voice": ["all"]},
    "refresh_interval": 0,
}
TG_CHANNEL_NAME = "TG Channel Name"
CHANNEL_NAME = "Custom Channel Name"


def platform_generic_path(_path: str) -> str:
    platform_specific_path: str = _path
    if platform.system() == "Windows":
        platform_specific_path = platform_specific_path.replace("/", "\\")
    return platform_specific_path


def mock_manage_duplicate_file(file_path: str) -> str:
    return file_path


class Chat:
    def __init__(self, chat_id):
        self.id = chat_id
        self.title = CHANNEL_NAME


class MockMessage:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.media = kwargs.get("media")
        self.audio = kwargs.get("audio", None)
        self.document = kwargs.get("document", None)
        self.photo = kwargs.get("photo", None)
        self.video = kwargs.get("video", None)
        self.voice = kwargs.get("voice", None)
        self.video_note = kwargs.get("video_note", None)
        self.chat = Chat(kwargs.get("chat_id", None))


class MockAudio:
    def __init__(self, **kwargs):
        self.file_name = kwargs["file_name"]
        self.mime_type = kwargs["mime_type"]


class MockDocument:
    def __init__(self, **kwargs):
        self.file_name = kwargs["file_name"]
        self.mime_type = kwargs["mime_type"]


class MockPhoto:
    def __init__(self, **kwargs):
        self.date = kwargs["date"]


class MockVoice:
    def __init__(self, **kwargs):
        self.mime_type = kwargs["mime_type"]
        self.date = kwargs["date"]


class MockVideo:
    def __init__(self, **kwargs):
        self.mime_type = kwargs["mime_type"]


class MockVideoNote:
    def __init__(self, **kwargs):
        self.mime_type = kwargs["mime_type"]
        self.date = kwargs["date"]


class MockEventLoop:
    def __init__(self):
        pass

    def run_until_complete(self, *args, **kwargs):
        return {
            "api_id": 1,
            "api_hash": "asdf",
            "chats": [
                {
                    "id": 12345,
                    "last_read_message_id": 0,
                    "ids_to_retry": [1, 2, 3],
                }
            ],
            "refresh_interval": 0,
        }


class MockAsync:
    def __init__(self):
        pass

    def get_event_loop(self):
        return MockEventLoop()


async def async_get_media_meta(message_media, _type, tg_chat_name, chat_name):
    result = await _get_media_meta(
        message_media, _type, tg_chat_name, chat_name
    )
    return result


async def async_download_media(
    client, message, media_types, file_formats, chat_name, chat_id
):
    result = await download_media(
        client, message, media_types, file_formats, chat_name, chat_id
    )
    return result


async def async_begin_import(conf, pagination_limit):
    result = await begin_import(conf, pagination_limit)
    return result


async def mock_process_message(*args, **kwargs):
    return 5


async def async_process_messages(
    client, messages, media_types, file_formats, chat_name, chat_id
):
    result = await process_messages(
        client, messages, media_types, file_formats, chat_name, chat_id
    )
    return result


class MockClient:
    def __init__(self, *args, **kwargs):
        pass

    def __aiter__(self):
        return self

    async def start(self):
        pass

    async def stop(self):
        pass

    async def get_chat_history(self, *args, **kwargs):
        items = [
            MockMessage(
                id=1213,
                media=True,
                voice=MockVoice(
                    mime_type="audio/ogg",
                    date=datetime(2019, 7, 25, 14, 53, 50),
                ),
            ),
            MockMessage(
                id=1214,
                media=False,
                text="test message 1",
            ),
            MockMessage(
                id=1215,
                media=False,
                text="test message 2",
            ),
            MockMessage(
                id=1216,
                media=False,
                text="test message 3",
            ),
        ]
        for item in items:
            yield item

    async def get_messages(self, *args, **kwargs):
        if kwargs["message_ids"] == 7:
            message = MockMessage(
                id=7,
                media=True,
                chat_id=123456,
                video=MockVideo(
                    file_name="sample_video.mov",
                    mime_type="video/mov",
                ),
            )
        elif kwargs["message_ids"] == 8:
            message = MockMessage(
                id=8,
                media=True,
                chat_id=234567,
                video=MockVideo(
                    file_name="sample_video.mov",
                    mime_type="video/mov",
                ),
            )
        elif kwargs["message_ids"] == [1]:
            message = [
                MockMessage(
                    id=1,
                    media=True,
                    chat_id=234568,
                    video=MockVideo(
                        file_name="sample_video.mov",
                        mime_type="video/mov",
                    ),
                )
            ]
        return message

    async def download_media(self, *args, **kwargs):
        mock_message = args[0]
        if mock_message.id in [7, 8]:
            raise pyrogram.errors.exceptions.bad_request_400.BadRequest
        elif mock_message.id == 9:
            raise pyrogram.errors.exceptions.unauthorized_401.Unauthorized
        elif mock_message.id == 11:
            raise TypeError
        return kwargs["file_name"]


class MediaDownloaderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.get_event_loop()

    @mock.patch("media_downloader.THIS_DIR", new=MOCK_DIR)
    def test_get_media_meta(self):
        # Test Voice notes
        message = MockMessage(
            id=1,
            media=True,
            voice=MockVoice(
                mime_type="audio/ogg",
                date=datetime(2019, 7, 25, 14, 53, 50),
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(
                message.voice, "voice", TG_CHANNEL_NAME, CHANNEL_NAME
            )
        )

        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/"
                    + CHANNEL_NAME
                    + "/voice/voice_2019-07-25T14:53:50.ogg"
                ),
                "ogg",
            ),
            result,
        )

        # Test photos
        message = MockMessage(
            id=2,
            media=True,
            photo=MockPhoto(date=datetime(2019, 8, 5, 14, 35, 12)),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(
                message.photo, "photo", TG_CHANNEL_NAME, CHANNEL_NAME
            )
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/" + CHANNEL_NAME + "/photo/"
                ),
                None,
            ),
            result,
        )

        # Test Documents
        message = MockMessage(
            id=3,
            media=True,
            document=MockDocument(
                file_name="sample_document.pdf",
                mime_type="application/pdf",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(
                message.document, "document", TG_CHANNEL_NAME, CHANNEL_NAME
            )
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/"
                    + CHANNEL_NAME
                    + "/document/sample_document.pdf"
                ),
                "pdf",
            ),
            result,
        )

        # Test audio
        message = MockMessage(
            id=4,
            media=True,
            audio=MockAudio(
                file_name="sample_audio.mp3",
                mime_type="audio/mp3",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(
                message.audio, "audio", TG_CHANNEL_NAME, CHANNEL_NAME
            )
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/" + CHANNEL_NAME + "/audio/sample_audio.mp3"
                ),
                "mp3",
            ),
            result,
        )

        # Test Video
        message = MockMessage(
            id=5,
            media=True,
            video=MockVideo(
                mime_type="video/mp4",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(
                message.video, "video", TG_CHANNEL_NAME, CHANNEL_NAME
            )
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/" + CHANNEL_NAME + "/video/"
                ),
                "mp4",
            ),
            result,
        )

        # Test VideoNote
        message = MockMessage(
            id=6,
            media=True,
            video_note=MockVideoNote(
                mime_type="video/mp4",
                date=datetime(2019, 7, 25, 14, 53, 50),
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(
                message.video_note, "video_note", TG_CHANNEL_NAME, CHANNEL_NAME
            )
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/"
                    + CHANNEL_NAME
                    + "/video_note/video_note_2019-07-25T14:53:50.mp4"
                ),
                "mp4",
            ),
            result,
        )

    @mock.patch("media_downloader.THIS_DIR", new=MOCK_DIR)
    @mock.patch("media_downloader.asyncio.sleep", return_value=None)
    @mock.patch("media_downloader.logger")
    def test_download_media(self, mock_logger, patched_time_sleep):
        client = MockClient()
        message = MockMessage(
            id=5,
            media=True,
            video=MockVideo(
                file_name="sample_video.mp4",
                mime_type="video/mp4",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client,
                message,
                ["video", "photo"],
                {"video": ["mp4"]},
                CHANNEL_NAME,
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(5, result)

        message_1 = MockMessage(
            id=6,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client,
                message_1,
                ["video", "photo"],
                {"video": ["all"]},
                CHANNEL_NAME,
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(6, result)

        # Test re-fetch message success
        message_2 = MockMessage(
            id=7,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
            chat=Chat(MOCK_CONF["chats"][0]["id"]),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client,
                message_2,
                ["video", "photo"],
                {"video": ["all"]},
                CHANNEL_NAME,
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(7, result)
        mock_logger.warning.assert_called_with(
            "Message[%d]: file reference expired, refetching...", 7
        )

        # Test re-fetch message failure
        message_3 = MockMessage(
            id=8,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client,
                message_3,
                ["video", "photo"],
                {"video": ["all"]},
                CHANNEL_NAME,
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(8, result)
        mock_logger.error.assert_called_with(
            "Message[%d]: file reference expired for 3 retries, download skipped.",
            8,
        )

        # Test other exception
        message_4 = MockMessage(
            id=9,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client,
                message_4,
                ["video", "photo"],
                {"video": ["all"]},
                CHANNEL_NAME,
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(9, result)
        mock_logger.error.assert_called_with(
            "Message[%d]: could not be downloaded due to following exception:\n[%s].",
            9,
            mock.ANY,
            exc_info=True,
        )

        # Check no media
        message_5 = MockMessage(
            id=10,
            media=None,
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client,
                message_5,
                ["video", "photo"],
                {"video": ["all"]},
                CHANNEL_NAME,
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(10, result)

        # Test timeout
        message_6 = MockMessage(
            id=11,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client,
                message_6,
                ["video", "photo"],
                {"video": ["all"]},
                CHANNEL_NAME,
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(11, result)
        mock_logger.error.assert_called_with(
            "Message[%d]: Timing out after 3 reties, download skipped.", 11
        )

    @mock.patch("__main__.__builtins__.open", new_callable=mock.mock_open)
    @mock.patch("media_downloader.yaml", autospec=True)
    def test_update_config(self, mock_yaml, mock_open):
        conf = {
            "api_id": 123,
            "api_hash": "hasw5Tgawsuj67",
            "chats": [
                {"id": "afsepo", "ids_to_retry": [], "last_read_message_id": 0}
            ],
            "refresh_interval": 0,
        }
        update_config(conf)
        mock_open.assert_called_with("config.yaml", "w")
        mock_yaml.dump.assert_called_with(conf, mock.ANY, default_flow_style=False)

    @mock.patch("media_downloader.update_config")
    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.process_messages", new=mock_process_message)
    def test_begin_import(self, mock_update_config):
        result = self.loop.run_until_complete(async_begin_import(MOCK_CONF, 3))
        conf = copy.deepcopy(MOCK_CONF)
        conf["chats"][0]["last_read_message_id"] = 5
        self.assertDictEqual(result, conf)

    def test_process_message(self):
        client = MockClient()
        result = self.loop.run_until_complete(
            async_process_messages(
                client,
                [
                    MockMessage(
                        id=1213,
                        media=True,
                        voice=MockVoice(
                            mime_type="audio/ogg",
                            date=datetime(2019, 7, 25, 14, 53, 50),
                        ),
                    ),
                    MockMessage(
                        id=1214,
                        media=False,
                        text="test message 1",
                    ),
                    MockMessage(
                        id=1215,
                        media=False,
                        text="test message 2",
                    ),
                    MockMessage(
                        id=1216,
                        media=False,
                        text="test message 3",
                    ),
                ],
                ["voice", "photo"],
                {"audio": ["all"], "voice": ["all"]},
                "channel_name",
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(result, 1216)

    @mock.patch("media_downloader._is_exist", return_value=True)
    @mock.patch(
        "media_downloader.manage_duplicate_file",
        new=mock_manage_duplicate_file,
    )
    def test_process_message_when_file_exists(self, mock_is_exist):
        client = MockClient()
        result = self.loop.run_until_complete(
            async_process_messages(
                client,
                [
                    MockMessage(
                        id=1213,
                        media=True,
                        voice=MockVoice(
                            mime_type="audio/ogg",
                            date=datetime(2019, 7, 25, 14, 53, 50),
                        ),
                    ),
                    MockMessage(
                        id=1214,
                        media=False,
                        text="test message 1",
                    ),
                    MockMessage(
                        id=1215,
                        media=False,
                        text="test message 2",
                    ),
                    MockMessage(
                        id=1216,
                        media=False,
                        text="test message 3",
                    ),
                ],
                ["voice", "photo"],
                {"audio": ["all"], "voice": ["all"]},
                "Chat Name",
                MOCK_CONF["chats"][0]["id"],
            )
        )
        self.assertEqual(result, 1216)

    def test_can_download(self):
        file_formats = {
            "audio": ["mp3"],
            "video": ["mp4"],
            "document": ["all"],
        }
        result = _can_download("audio", file_formats, "mp3")
        self.assertEqual(result, True)

        result1 = _can_download("audio", file_formats, "ogg")
        self.assertEqual(result1, False)

        result2 = _can_download("document", file_formats, "pdf")
        self.assertEqual(result2, True)

        result3 = _can_download("document", file_formats, "epub")
        self.assertEqual(result3, True)

    def test_is_exist(self):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        result = _is_exist(os.path.join(this_dir, "__init__.py"))
        self.assertEqual(result, True)

        result1 = _is_exist(os.path.join(this_dir, "init.py"))
        self.assertEqual(result1, False)

        result2 = _is_exist(this_dir)
        self.assertEqual(result2, False)

    @mock.patch("media_downloader.FAILED_IDS", {"asdf": [2, 3]})
    @mock.patch("media_downloader.yaml.safe_load")
    @mock.patch("media_downloader.update_config", return_value=True)
    @mock.patch("media_downloader.begin_import")
    @mock.patch("media_downloader.asyncio", new=MockAsync())
    def test_main(self, mock_import, mock_update, mock_yaml):
        conf = {
            "api_id": 1,
            "api_hash": "asdf",
            "chats": [
                {
                    "id": 12345,
                    "last_read_message_id": 0,
                    "ids_to_retry": [1, 2],
                }
            ],
            "refresh_interval": 0,
        }

        mock_yaml.return_value = conf
        main()
        mock_import.assert_called_with(conf, pagination_limit=100)
        conf["chats"][0]["ids_to_retry"] = [1, 2, 3]
        mock_update.assert_called_with(conf)
    
    #only tests loop functionality
    @mock.patch("media_downloader.yaml.safe_load")
    @mock.patch("media_downloader.update_config", return_value=True)
    @mock.patch("media_downloader.begin_import")
    @mock.patch("media_downloader.asyncio", new=MockAsync())
    @mock.patch("media_downloader.sleep", side_effect=InterruptedError)
    def test_main_sleep(self, mock_sleep, mock_import, mock_update, mock_yaml):
        conf = {
            "api_id": 1,
            "api_hash": "asdf",
            "chats": [
                {
                    "id": 12345,
                    "last_read_message_id": 0,
                    "ids_to_retry": [],
                }
            ],
            "refresh_interval": 1,
        }

        mock_yaml.return_value = conf
        main()
        mock_sleep.assert_called_with(conf["refresh_interval"] * 60)

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()
