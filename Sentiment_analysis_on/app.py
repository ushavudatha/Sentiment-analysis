from flask import Flask, request, render_template
from pprint import pprint
import nltk
import yaml
import sys
import os
import re
#import matplotlib.pyplot as plt
app=Flask(__name__)
positive=0
negative=0
@app.route('/')
def my_form():
    return render_template('form.html')
    
class Splitter(object):

    def __init__(self):
        self.nltk_splitter = nltk.data.load('tokenizers/punkt/english.pickle')
        self.nltk_tokenizer = nltk.tokenize.TreebankWordTokenizer()

    def split(self, text):
        """
        input format: a paragraph of text
        output format: a list of lists of words.
            e.g.: [['this', 'is', 'a', 'sentence'], ['this', 'is', 'another', 'one']]
        """
        sentences = self.nltk_splitter.tokenize(text)
        tokenized_sentences = [self.nltk_tokenizer.tokenize(sent) for sent in sentences]
        return tokenized_sentences


class POSTagger(object):

    def __init__(self):
        pass
        
    def pos_tag(self, sentences):
        """
        input format: list of lists of words
            e.g.: [['this', 'is', 'a', 'sentence'], ['this', 'is', 'another', 'one']]
        output format: list of lists of tagged tokens. Each tagged tokens has a
        form, a lemma, and a list of tags
            e.g: [[('this', 'this', ['DT']), ('is', 'be', ['VB']), ('a', 'a', ['DT']), ('sentence', 'sentence', ['NN'])],
                    [('this', 'this', ['DT']), ('is', 'be', ['VB']), ('another', 'another', ['DT']), ('one', 'one', ['CARD'])]]
        """

        pos = [nltk.pos_tag(sentence) for sentence in sentences]
        #adapt format
        pos = [[(word, word, [postag]) for (word, postag) in sentence] for sentence in pos]
        return pos

class DictionaryTagger(object):

    def __init__(self, dictionary_paths):
        files = [open(path, 'r') for path in dictionary_paths]
        dictionaries = [yaml.safe_load(dict_file) for dict_file in files]
        map(lambda x: x.close(), files)
        self.dictionary = {}
        self.max_key_size = 0
        for curr_dict in dictionaries:
            for key in curr_dict:
                if key in self.dictionary:
                    self.dictionary[key].extend(curr_dict[key])
                else:
                    self.dictionary[key] = curr_dict[key]
                    self.max_key_size = max(self.max_key_size, len(key))

    def tag(self, postagged_sentences):
        return [self.tag_sentence(sentence) for sentence in postagged_sentences]

    def tag_sentence(self, sentence, tag_with_lemmas=False):
        """
        the result is only one tagging of all the possible ones.
        The resulting tagging is determined by these two priority rules:
            - longest matches have higher priority
            - search is made from left to right
        """
        tag_sentence = []
        N = len(sentence)
        if self.max_key_size == 0:
            self.max_key_size = N
        i = 0
        while (i < N):
            j = min(i + self.max_key_size, N) #avoid overflow
            tagged = False
            while (j > i):
                expression_form = ' '.join([word[0] for word in sentence[i:j]]).lower()
                #print(expression_form)
                expression_lemma = ' '.join([word[1] for word in sentence[i:j]]).lower()
                #print(expression_lemma)
                if tag_with_lemmas:
                    literal = expression_lemma
                else:
                    literal = expression_form
                #print(literal)    
                if literal in self.dictionary:
                    #self.logger.debug("found: %s" % literal)
                    is_single_token = j - i == 1
                    #print(is_single_token)
                    original_position = i
                    #print(original_position)
                    i = j
                    taggings = [tag for tag in self.dictionary[literal]]
                    #print(taggings)
                    tagged_expression = (expression_form, expression_lemma, taggings)
                    #print(tagged_expression)
                    if is_single_token: #if the tagged literal is a single token, conserve its previous taggings:
                        original_token_tagging = sentence[original_position][2]
                        #print(original_token_tagging)
                        #print(tagged_expression)
                        tagged_expression[2].extend(original_token_tagging)
                        #print(tagged_expression)
                    tag_sentence.append(tagged_expression)
                    
                    tagged = True
                else:
                    j = j - 1
            if not tagged:
                tag_sentence.append(sentence[i])
                #print(tag_sentence)
                i += 1
        return tag_sentence

def value_of(sentiment):
    global positive
    global negative
    if sentiment == 'positive': 
        positive+=1
        return 1
    if sentiment == 'negative':
        negative+=1
        return -1
    return 0

def sentence_score(sentence_tokens, previous_token, acum_score):
    global positive
    global negative   
    if not sentence_tokens:
        return acum_score
    else:
        current_token = sentence_tokens[0]
        tags = current_token[2]
        token_score = sum([value_of(tag) for tag in tags])
        if previous_token is not None:
            previous_tags = previous_token[2]
            if 'inc' in previous_tags:
                token_score *= 2.0
            elif 'dec' in previous_tags:
                token_score /= 2.0
            elif 'inv' in previous_tags:
                token_score *= -1.0
        if(acum_score+token_score==-1.0):
            positive-=1
            negative+=1
        elif(acum_score+token_score==1.0):
            positive+=1
            negative-=1
        elif(acum_score+token_score==-2.0):
            #positive-=1
            negative+=1
        elif(acum_score+token_score==2.0):
            positive+=1
            #negative+=1 
        elif(acum_score+token_score==-0.5):
            #positive-=1
            negative+=1
        elif(acum_score+token_score==0.5):
            positive+=1        
        return sentence_score(sentence_tokens[1:], current_token, acum_score + token_score)

def sentiment_score(review):
    return sum([sentence_score(sentence, None, 0.0) for sentence in review])
#def percentage(uper, lower):
#    global uper
#    return 100*float(uper)/float(lower)
#if __name__ == "__main__":
    #text="""too poor"""
    #user input must be dynamic(from front-end)
    #object creation.
    
    
    #print(score)
    #if score<0:
    #    print("Negative")
    #elif score>0:
    #    print("Positive")
    #else:
    #    print("Neutral")
    
@app.route('/', methods=['POST'])
def my_form_post():
    text = request.form['text']
    global positive
    global negative
    splitter = Splitter()
    postagger = POSTagger()
    dicttagger = DictionaryTagger([ 'dicts/positive.yml', 'dicts/negative.yml', 
                                    'dicts/inc.yml', 'dicts/dec.yml', 'dicts/inv.yml'])

    splitted_sentences = splitter.split(text)
    #pprint(splitted_sentences)
    #print(splitted_sentences)
    #print("--------------------------------------------------")
    pos_tagged_sentences = postagger.pos_tag(splitted_sentences)
    #pprint(pos_tagged_sentences)
    #print("--------------------------------------------------")
    dict_tagged_sentences = dicttagger.tag(pos_tagged_sentences)
    #pprint(dict_tagged_sentences)
    #print("--------------------------------------------------")
    #print("analyzing sentiment...")
    score = sentiment_score(dict_tagged_sentences)
    if score<0:
        ans="Negative"
    elif score>0:
        ans="Positive"
    elif score==0:
        ans="Neutral"
    positive=100*float(positive)/float(100)
    negative=100*float(negative)/float(100)

    #labels=['[positive]', '[negative]']
    #sizes=[positive,negative]
    #colors=['yellowgreen',"red"]
    #chart=plt.pie(sizes,labels=labels, startangle=90, autopct='%.2f%%',shadow=True)
    #plt.title("[PIE CHART REPRESENTATION]")
    #plt.axis("equal")
    #plt.tight_layout()
    #plt.show()    
    return render_template('form.html', text=text, final=score, ans=ans)
    
    
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5002, threaded=True)    