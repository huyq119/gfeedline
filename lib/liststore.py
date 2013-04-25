#
# gfeedline - A Social Networking Client
#
# Copyright (c) 2012, Yoshizumi Endo.
# Licence: GPL3

from gi.repository import GdkPixbuf

from window import MainWindow
from view import FeedView
from constants import Column
from accountliststore import AccountListStore
from filterliststore import FilterListStore
from utils.liststorebase import ListStoreBase, SaveListStoreBase
from plugins.twitter.output import TwitterOutputFactory

from plugins.twitter.api import TwitterAPIDict
from plugins.facebook.api import FacebookAPIDict
from plugins.tumblr.api import TumblrAPIDict


class FeedListStore(ListStoreBase):

    """ListStore for Feed Sources.

    0,     1,    2,      3,        4,    5,      6,
    group, icon, source, username, name, target, argument,

    7,            8,           9
    options_dict, account_obj, api_obj
    """

    def __init__(self):
        super(FeedListStore, self).__init__(
            str, GdkPixbuf.Pixbuf, str, str, str, str, str, object, object, object)

        self.account_liststore = AccountListStore()
        self.filter_liststore = FilterListStore()

        self.window = MainWindow(self)
        self.api_dict = TwitterAPIDict()

        self.save = SaveListStore()
        for entry in self.save.load():
            self.append(entry)

    def append(self, source, iter=None):
        # FIXME:Facebook
        source_name = source.get('source')
        if source_name == 'Twitter':
            api_class = self.api_dict.get(source['target'])
        elif source_name == 'Facebook':
            api_class = FacebookAPIDict().get(source['target'])
        else:
            api_class = TumblrAPIDict().get(source['target'])

        account_obj = self.account_liststore.get_account_obj(
            source.get('source'), source.get('username'))

        if not api_class or not account_obj:
            return

        api = api_class(account_obj)
        notebook = self.window.get_notebook(source.get('group'))

        for row in self:
            if (source.get('name') == row[Column.API].view.name and 
                source.get('group') == row[Column.GROUP] and 
                source.get('source') == row[Column.SOURCE]):
                view = row[Column.API].view
                view.feed_counter += 1
                break
        else:
            page = int(str(self.get_path(iter))) if iter else -1
            tab_name = source.get('name') or api.name
            view = FeedView(self, notebook, api, tab_name, page)

        factory = TwitterOutputFactory()
        api_obj = factory.create_obj(api, view, 
                                     source.get('argument'), source.get('options'),
                                     self.filter_liststore)

        list = [source.get('group'),
                account_obj.icon.get_pixbuf(),
                source.get('source'),
                source.get('username'),
                source.get('name'),
                source['target'], # API 
                source.get('argument'), 
                source.get('options'),
                account_obj,
                api_obj]

        new_iter = self.insert_before(iter, list)

        interval = 40 if api.name == 'Home TimeLine' else 180
        api_obj.start(interval)

        return new_iter

    def update(self, source, iter):
        old_column = [Column.GROUP, Column.SOURCE, Column.USERNAME, 
                      Column.NAME, Column.TARGET, Column.ARGUMENT]
        old = [self.get_value(iter, x).decode('utf-8') for x in old_column]
        new = [source.get(x) for x in ['group', 'source', 'username', 
                                       'name', 'target', 'argument']]

        if old != new:
            new_iter = self.append(source, iter)
            self.remove(iter)
        else:
            new_iter = iter

            # API
            api_obj = self.get_value(iter, Column.API)
            api_obj.options = source.get('options', {})
            self.set_value(iter, Column.OPTIONS, api_obj.options)

        return new_iter

    def remove(self, iter):
        api = self.get_value(iter, Column.API)
        api.exit()
        del api
        super(FeedListStore, self).remove(iter)

    def get_group_page(self, target_group):
        group_list = self.get_group_list()

        return group_list.index(target_group) \
            if target_group in group_list else 0

    def get_group_list(self):
        group_list =[]
        for x in self:
            group = x[Column.GROUP].decode('utf-8')
            if group not in group_list:
                group_list.append(group)
        
        return group_list

class SaveListStore(SaveListStoreBase):

    SAVE_FILE = 'feed_sources.json'

    def _parse_entry(self, entry):
        source_list = []

        for dir in entry:
            data = { 'name' : '', 'target' : '', 'argument' : '',
                     'source' : 'Twitter', 'username': '',
                     'options' : {} }

            for key, value in dir.items():
                if key in ['group', 'source', 'username', 
                           'name', 'target', 'argument']:
                    data[key] = value
                else:
                    data['options'][key] = value

            source_list.append(data)

        # print source_list
        return source_list

    def save(self, liststore):
        data_list = ['source', 'username', 'name', 'target', 'argument']
        save_data = []

        for i, row in enumerate(liststore):
            save_temp = {'group': row[Column.GROUP]} # fixme

            for num, key in enumerate(data_list):
                value = row[num+Column.SOURCE] # liststore except icon.
                if value is not None:
                    save_temp[key] = value

            if row[Column.OPTIONS]:
                for key, value in row[Column.OPTIONS].iteritems():
                    save_temp[key] = value
                    # print key, value
            save_data.append(save_temp)

        # print save_data
        self.save_to_json(save_data)
