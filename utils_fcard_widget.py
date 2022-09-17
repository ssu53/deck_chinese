import numpy as np
import pandas as pd
import datetime
import pickle

import urllib.request
from bs4 import BeautifulSoup

from random import choice, choices

from IPython.display import clear_output
import ipywidgets as widgets



class Flashcards():
    
    
    def __init__(self, fname=None, source='Augen auf China 20-30', score=0):
        """
        TODO: persistent ui should be separate from initialisation
        TODO: refactor
        """
                
        if fname is None: 
            self.deck = pd.DataFrame(columns=['char', 'pinyin', 'eng', 'source','score'], dtype=object)
        else:             
            with open(fname, 'rb') as f: self.deck = pickle.load(f)
        
        self.batch_set = []
        
        self.ind = len(self.deck) # DataFrame index for the next write.
        self.w_char = widgets.Text(value=None, description='char')
        self.w_pinyin = widgets.Text(value=None, description='pinyin')
        self.w_eng = widgets.Text(value=None, description='eng')
        self.w_source = widgets.Text(value=source, description='source')
        self.w_score = widgets.Text(value=str(score), description='score')
        
        self.w_button_lookup = widgets.Button(description='Lookup char')
        self.w_exact = widgets.Checkbox(description='Exact')
        self.w_button_add = widgets.Button(description='Add')
        self.w_button_next = widgets.Button(description='Next')
        
        self.w_deck = widgets.Output()
        with self.w_deck: display(self.deck.tail(15))
        
        self.w_lookup_label = widgets.HTML(value='')
        self.w_lookup = widgets.Output()
            
        self.w_dupl_label = widgets.HTML(value='')
        self.w_dupl = widgets.Output()
        
        self.w_message = widgets.HTML(value='')
        

        def button_add(_):
            if self.w_button_add.description == 'Overwrite':
                self.ind = self.deck[self.deck['char'] == self.w_char.value].index[0] 
            elif self.w_char.value in list(self.deck['char']):
                self.w_button_add.description = 'Overwrite'
                with self.w_dupl:
                    clear_output()
                    display(pd.concat([self.deck[self.deck['char'] == self.w_char.value],
                       pd.DataFrame([[self.w_char.value,self.w_pinyin.value,self.w_eng.value,self.w_source.value,self.w_score.value]], index=['new'], columns=self.deck.columns)
                      ]))
                return
            else:
                self.ind = len(self.deck)
            #button_lookup(_)
            self.deck.loc[self.ind, :] = self.w_char.value, self.w_pinyin.value, self.w_eng.value, self.w_source.value, int(self.w_score.value)
            self.deck.reset_index(drop=True, inplace=True)
            self.w_dupl_label.value = ''
            if self.w_button_add.description == 'Add': 
                with self.w_dupl: clear_output()
            self.w_message.value = "Wrote to index " + str(self.ind) + " in deck."
            with self.w_deck: 
                clear_output()
                display(self.deck.tail(15))
            self.w_lookup_label.value = ''
            with self.w_lookup: clear_output()
            self.w_button_add.description = 'Add'
        self.w_button_add.on_click(button_add)
        

        def button_next(_):
            self.ind = len(self.deck)
            self.w_button_add.description = 'Add'
            self.w_char.value = ''
            self.w_pinyin.value = ''
            self.w_eng.value = ''
            self.w_lookup_label.value = ''
            self.w_dupl_label.value = ''
            with self.w_lookup: clear_output()
            with self.w_dupl: clear_output()
            self.w_message.value = ''
        self.w_button_next.on_click(button_next)
        

        def button_lookup(_):
            df_lookup = self.lookup(char=self.w_char.value, exact=self.w_exact.value)
            self.w_button_add.description = 'Add'
            self.w_lookup_label.value =  "<p style='font-size:large'>Dictionary</p>"
            if len(df_lookup) != 0:
                self.w_pinyin.value = df_lookup.loc[0,'pinyin']
                self.w_eng.value = df_lookup.loc[0,'eng']
            with self.w_lookup:
                clear_output()
                display(df_lookup)
            self.w_dupl_label.value = "<p style='font-size:large'>In deck</p>"
            with self.w_dupl:
                clear_output()
                display(self.deck[self.deck['char'] == self.w_char.value])
            self.w_message.value = ''
        self.w_button_lookup.on_click(button_lookup)
        
        
        # Display user interface.
        self.ui = widgets.HBox([
            widgets.VBox([
                widgets.HTML(value="<p style='font-size:large'>Edit deck</p>"),
                widgets.HBox([
                    widgets.VBox([self.w_char, self.w_pinyin, self.w_eng, self.w_source, self.w_score], layout={'height':'180px'}),
                    widgets.VBox([self.w_button_lookup, self.w_exact, self.w_button_add, self.w_button_next])
                ]),
                widgets.VBox([
                    widgets.HTML(value="<p style='font-size:large'>Deck</p>"), self.w_deck], layout={'min_height':'60px', 'width':'650px'})]),
                    widgets.VBox([self.w_lookup_label, self.w_lookup, self.w_dupl_label, self.w_dupl,self.w_message], layout={'width':'450px'})
            ])
        
        display(self.ui)

    
    def lookup(self, char, exact=False):
        """
        Looks up char(s) in the Chinese dictionary at chinese.yabla.com
        If exact, populates grid with only exact matches
        """

        query_utf8 = char.encode('utf-8')
        query_hex = ''

        for i in range(len(query_utf8)):
            query_hex += '%' + str(hex(query_utf8[i]))[2:]

        url_stem = 'https://chinese.yabla.com/chinese-english-pinyin-dictionary.php?define='
        url = url_stem + query_hex
        
        df_extracted = self.__scrape_dict(url)
        if not exact: return df_extracted
        
        if exact: return df_extracted[df_extracted['char'] == char]
    
        if char in list(self.deck['char']): 
            print('Match in this deck')
            print(self.deck[self.deck['char'] == char])
            usr_input = input('Overwrite?')
            while (usr_input != 'y') and (usr_input != 'n'):
                usr_input = input('Answer y/n.')
            if usr_input == 'y': self.overwrite(char)
            if usr_input == 'n': return
        else:
            usr_input = input('No match in this deck. Add?')
            while (usr_input != 'y') and (usr_input != 'n'):
                usr_input = input('Answer y/n.')
            if usr_input == 'n': return
            pinyin = input('pinying for the char ' + char + ':')
            eng = input('eng for the char ' + char + ':')
            source = input('source for the char ' + char + ':')
            if not source: source = None
            self.add(char, pinyin, eng, source)
    
    
    def __scrape_dict(self, url, n_results=10):
        """
        scrapes the Chinese dictionary at the url
        gets the top n_results
        returns DataFrame of extracted contents (characters, pinyin, english)
        """

        request = urllib.request.Request(url)
        html = urllib.request.urlopen(request).read()

        soup = BeautifulSoup(html, 'html.parser')
        main_table = soup.find('ul', attrs={'id':'search_results'})
        chars = main_table.find_all('span', class_='word')
        defs = main_table.find_all('div', class_='definition')

        # Remove whitespace.
        chars_stripped = [x.text.strip() for x in chars]

        # Remove tradtitional characters.
        chars_simp = list(filter(lambda x: not x.startswith('Trad'), chars_stripped))

        # Restrict to top n_results results.
        chars_simp = chars_simp[:n_results]
        defs = defs[:n_results]

        df_extracted = pd.DataFrame(columns=['char', 'pinyin', 'eng'], dtype=object)
        if len(defs) != len(chars_simp):
            raise Exception() 

        for i in range(len(chars_simp)):           
            char = chars_simp[i]
            df_extracted.loc[i, 'char'] = char

            chunks = list(filter(None, defs[i].text.split('\n')))    
            df_extracted.loc[i, 'pinyin'] = chunks[0]
            
            defin_list = chunks[1:] 
            defin_str = ''
            for defin in defin_list: defin_str += defin + ', '
            df_extracted.loc[i, 'eng'] = defin_str[:-2]

        # Reindex to order by length of word in Chinese. Mergesort is the only stable.
        reind = df_extracted['char'].str.len().sort_values(kind='mergesort').index
        df_extracted = df_extracted.reindex(reind)
        df_extracted.reset_index(drop=True, inplace=True)

        return df_extracted
    
        
    def remove(self, char):
        """
        remove char from deck
        """

        if char in list(self.deck['char']):
            ind = self.deck[self.deck['char'] == char].index[0]
            print('Undo by: ')
            print("add('" + self.deck.loc[ind,'char'] + "', '" + self.deck.loc[ind,'pinyin'] + "', '" +
                  self.deck.loc[ind,'eng'] + "')")
            self.deck.drop(index=ind, inplace=True)
            self.deck.reset_index(drop=True, inplace=True)
        else:
            print('Not in deck.')
     
    
    def shuffle(self, damp=0, source=None):
        """
        Shuffle through cards in the deck
        damp: exponentially weighted damping that controls frequency of appearance of frequently mistaken cards
        source: optional, subset of the deck by source
        """
        
        if source is None: deck_subset = self.deck
        else: deck_subset = self.get_source(source)
            
        w_damp = widgets.FloatSlider(value=damp, min=damp-5, max=damp+5, step=1, layout=widgets.Layout(width='300px'), description='Damp')
        w_front = widgets.HTML(layout={'min-height':'30px', 'width':'500px', 'margin':'2px 10px 0px 10px'})
        w_back = widgets.HTML(layout={'min-height':'50px', 'width':'500px', 'margin':'2px 10px 0px 10px'})
        w_stuff = widgets.HTML(layout={'min-height':'15px', 'width':'500px', 'margin':'0px 10px 0px 10px'})
        w_button_reveal = widgets.Button(description='Reveal')
        w_button_yes = widgets.Button(description='Yes')
        w_button_no = widgets.Button(description='No')
        
        self.ind = choices(deck_subset.index.values, 
                           weights=np.fromiter(map(np.exp, -w_damp.value * deck_subset['score'].values), dtype=float), 
                           k=1)[0]
        w_front.value = "<p style='font-size:xx-large'>" + deck_subset.loc[self.ind,'char'] + "</p>"
        

        def button_reveal(_):
            if w_button_reveal.description == 'Reveal':
                w_back.value = "<p style='font-size:medium; line-height:1em'>" + self.deck.loc[self.ind,'pinyin'] + \
                                 "<br/>" + self.deck.loc[self.ind,'eng'] + "</p>" 
                w_stuff.value = "<p style='font-size:small'>" + str(self.ind) + " | " + self.deck.loc[self.ind,'source'] + \
                                " | Score: " + str(self.deck.loc[self.ind,'score']) + "</p>"
                w_button_reveal.description = 'Hide'
            elif w_button_reveal.description == 'Hide':
                w_back.value = ""
                w_stuff.value = ""
                w_button_reveal.description = 'Reveal'
        w_button_reveal.on_click(button_reveal)
        

        def button_yes(_):
            self.deck.loc[self.ind, 'score'] += 1
            deck_subset = self.get_source(source)
            self.ind = choices(deck_subset.index.values, 
              weights=np.fromiter(map(np.exp, -w_damp.value * deck_subset['score'].values), dtype=float), 
              k=1)[0]
            w_front.value = "<p style='font-size:xx-large'>" + deck_subset.loc[self.ind,'char'] + "</p>"
            w_back.value = ""
            w_stuff.value = ""
            w_button_reveal.description = 'Reveal'
        w_button_yes.on_click(button_yes)
        

        def button_no(_):
            self.deck.loc[self.ind, 'score'] -= 1
            deck_subset = self.get_source(source)
            self.ind = choices(deck_subset.index.values, 
              weights=np.fromiter(map(np.exp, -w_damp.value * deck_subset['score'].values), dtype=float), 
              k=1)[0]
            w_front.value = "<p style='font-size:xx-large'>" + deck_subset.loc[self.ind,'char'] + "</p>"
            w_back.value = ""
            w_stuff.value = ""
            w_button_reveal.description = 'Reveal'
        w_button_no.on_click(button_no)
            
        
        display(widgets.HBox([widgets.VBox([w_front, w_back, w_stuff]), 
                              widgets.VBox([widgets.HBox([w_button_reveal, w_button_yes, w_button_no]), 
                                            w_damp], layout={'height':'95px'})]))
                
    
    def batch(self, batch_size=10, source=None):
        """
        In batch mode, get each item in the batch correct twice to remove from batch
        batch_size is the number of cards in batch
        source: optional, subset of the deck by source
        """
        
        if len(self.batch_set) == 0:
            
            if source is None: deck_subset = self.deck
            else: deck_subset = self.get_source(source)
            
            self.batch_set = list(deck_subset.sort_values(by='score', kind='mergesort').index[:batch_size])
            self.batch_set += self.batch_set # 2x duplicate.
            
        
        w_message = widgets.HTML(value=str(len(np.unique(self.batch_set))) + ' remaining in batch...')
        w_front = widgets.HTML(layout={'min-height':'30px', 'width':'500px', 'margin':'2px 10px 0px 10px'})
        w_back = widgets.HTML(layout={'min-height':'50px', 'width':'500px', 'margin':'2px 10px 0px 10px'})
        w_stuff = widgets.HTML(layout={'min-height':'15px', 'width':'500px', 'margin':'0px 10px 0px 10px'})
        w_button_reveal = widgets.Button(description='Reveal')
        w_button_yes = widgets.Button(description='Yes')
        w_button_no = widgets.Button(description='No')
        

        self.ind = choice(self.batch_set)
        w_front.value = "<p style='font-size:xx-large'>" + self.deck.loc[self.ind,'char'] + "</p>"
        

        def button_reveal(_):
            if w_button_reveal.description == 'Reveal':
                w_back.value = "<p style='font-size:medium; line-height:1em'>" + self.deck.loc[self.ind,'pinyin'] + \
                                 "<br/>" + self.deck.loc[self.ind,'eng'] + "</p>" 
                w_stuff.value = "<p style='font-size:small'>" + str(self.ind) + " | " + self.deck.loc[self.ind,'source'] + \
                                " | Score: " + str(self.deck.loc[self.ind,'score']) + "</p>"
                w_button_reveal.description = 'Hide'
            elif w_button_reveal.description == 'Hide':
                w_back.value = ""
                w_stuff.value = ""
                w_button_reveal.description = 'Reveal'
        w_button_reveal.on_click(button_reveal)
        

        def button_yes(_):
            if len(self.batch_set) == 0: return
            self.batch_set.remove(self.ind)
            if self.ind not in self.batch_set: self.deck.loc[self.ind,'score'] += 1
            if len(self.batch_set) == 0: 
                w_message.value = 'Batch complete.'
                return
            else: w_message.value = str(len(np.unique(self.batch_set))) + ' remaining in batch...'
            self.ind = choice(self.batch_set)
            w_front.value = "<p style='font-size:xx-large'>" + self.deck.loc[self.ind,'char'] + "</p>"
            w_back.value = ""
            w_stuff.value = ""
            w_button_reveal.description = 'Reveal'
        w_button_yes.on_click(button_yes)
        

        def button_no(_):
            if len(self.batch_set) == 0: return
            self.batch_set.append(self.ind)
            if len(self.batch_set) == 0: 
                w_message.value = 'Batch complete.'
                return
            else: w_message.value = str(len(np.unique(self.batch_set))) + ' remaining in batch...'
            self.ind = choice(self.batch_set)
            w_front.value = "<p style='font-size:xx-large'>" + self.deck.loc[self.ind,'char'] + "</p>"
            w_back.value = ""
            w_stuff.value = ""
            w_button_reveal.description = 'Reveal'
        w_button_no.on_click(button_no)
        
            
        display(
            widgets.HBox([
                widgets.VBox([w_front, w_back, w_stuff]), 
                widgets.VBox([widgets.HBox([w_button_reveal, w_button_yes, w_button_no]), 
                w_message], layout={'height':'95px'})]))
            
    
    def batch_members(self):
        """
        view cards in the current batch
        """

        if len(self.batch_set) == 0:
            print('No defined batch.')
            return
        
        display(self.deck.loc[set(self.batch_set),:])
    
    
    def import_txt(self, fname, source):
        """
        import the flashcards downloaded externally into the deck
        """
        
        class DictAtt(Enum):
            char = 0
            pinyin = 1
            eng = 2
            
        with open(fname) as f:
            lines = f.readlines()

        pre_len = len(self.deck)
        
        dict_att = DictAtt.char
        
        for line in tqdm(lines):
            
            if not line.strip():
                dict_att = DictAtt.char
                continue
            
            if dict_att == DictAtt.char: char = line.strip()
            if dict_att == DictAtt.pinyin: pinyin = line.strip()
            if dict_att == DictAtt.eng: eng = line.strip()

            if dict_att == DictAtt.eng: 
                self.add(char, pinyin, eng, source)
            dict_att = DictAtt((dict_att.value+1) % 3)
            
        post_len = len(self.deck)
        print('Added ' + str(post_len-pre_len) + ' entries to deck.')
        
    
    def export_txt(self, fname):
        """
        TODO: export deck state to txt
        """
        pass
    
    
    def pickle_me(self, directory='deck/'):
        """
        save deck contents to directory
        datestamps it
        """
        with open(directory + 'deck_' + datetime.datetime.now().strftime('%Y%m%d_%H%M'), 'wb') as f:
            pickle.dump(self.deck, f)
    
    
    def show(self):
        display(self.deck)
        
    
    def get_index(self, ind):
        return self.deck.loc[self.deck.index == ind]
    
    
    def get_char(self, char, exact=False):
        if exact: return self.deck[self.deck['char'] == char]
        else: return self.deck[self.deck['char'].str.contains(char)]

    
    def get_eng(self, eng, exact=False):
        if exact: return self.deck[self.deck['eng'] == eng]
        else: return self.deck[self.deck['eng'].str.contains(eng)]

        
    def get_source(self, source, exact=False):
        if exact: return self.deck[self.deck['source'] == source]
        else: return self.deck[self.deck['source'].str.contains(source)]
    
    
    def get_score(self, score=None):
        if score is None: return self.deck[self.deck['score'] != 0]
        return self.deck[self.deck['score'] == score]
    
    
    def show_progress(self):
        """
        display progress as table of % positive / negative / neither scores for each subdeck
        """

        prog = pd.DataFrame()

        for source in self.deck['source'].unique():

            df = self.get_source(source)

            prog.loc[source, '0'] = len(df[df['score'] == 0]) / len(df) * 100
            prog.loc[source, '+'] = len(df[df['score'] > 0]) / len(df) * 100
            prog.loc[source, '-'] = len(df[df['score'] < 0]) / len(df) * 100
            prog.loc[source, '#'] = len(df)
        
        prog.loc['All', '0'] = len(self.deck[self.deck['score'] == 0]) / len(self.deck) * 100
        prog.loc['All', '+'] = len(self.deck[self.deck['score'] > 0]) / len(self.deck) * 100
        prog.loc['All', '-'] = len(self.deck[self.deck['score'] < 0]) / len(self.deck) * 100
        prog.loc['All', '#'] = len(self.deck)

        display(prog.style.format({'0':'{:.2f}','+':'{:.2f}','-':'{:.2f}','#':'{:.0f}'}))

