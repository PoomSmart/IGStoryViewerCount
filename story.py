import codecs
import csv
import json

from instagram_private_api import Client, ClientCompatPatch

username = 'yourusername'
password = 'yourpassword'
cached_media = False


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def get_user_id(self, username):
    res = self._call_api('users/%s/usernameinfo/' % (username))
    return res['user']['pk']


def reels_media_story(self, user_ids, media_id, **kwargs):
    """
    Get multiple users' reel/story media

    :param user_ids: list of user IDs
    :param kwargs:
    :return:
    """
    user_ids = [str(x) for x in user_ids]
    params = {'user_ids': user_ids, 'media_id': media_id}
    params.update(kwargs)

    res = self._call_api('feed/reels_media/', params=params)
    if self.auto_patch:
        for reel_media in res.get('reels_media', []):
            [ClientCompatPatch.media(m, drop_incompat_keys=self.drop_incompat_keys)
             for m in reel_media.get('items', [])]
        for _, reel in list(res.get('reels', {}).items()):
            [ClientCompatPatch.media(m, drop_incompat_keys=self.drop_incompat_keys)
             for m in reel.get('items', [])]
    return res


with open('settings') as file_data:
    cached_settings = json.load(file_data, object_hook=from_json)
    print('Reusing settings: {0!s}'.format('settings'))

    device_id = cached_settings.get('device_id')
    api = Client(username, password, settings=cached_settings)

user_id = get_user_id(api, username)

archived_stories = api.stories_archive() if not cached_media else None
if archived_stories is None or archived_stories.get('items'):
    if archived_stories is not None:
        item_ids = [a['id'] for a in archived_stories['items']]
        archived_stories_media = api.reels_media(user_ids=item_ids)
        with open('media.json', 'w') as outfile:
            outfile.write(json.dumps(archived_stories_media, indent=4, sort_keys=True))
    else:
        with open('media.json') as infile:
            archived_stories_media = json.load(infile)
    counter = {}
    total_viewer_count = 0
    for name, media in archived_stories_media['reels'].items():
        items = media['items'][0]
        media_id = media['cover_media']['media_id']
        viewer_count = items['total_viewer_count']
        print('process %s' % media_id)

        total_viewer_count += viewer_count
        result = api.story_viewers(media_id)
        viewers = result['users']
        for viewer in viewers:
            username = viewer['username']
            if username in counter:
                counter[username] += 1
            else:
                counter[username] = 1

    # print(json.dumps(counter, indent=4, sort_keys=True))
    print(total_viewer_count)
    with open('report.csv', 'w') as csv_file:
        writer = csv.writer(csv_file)
        for key, value in counter.items():
            writer.writerow([key, value])
