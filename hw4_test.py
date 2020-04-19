# -*- coding: utf-8 -*-
"""hw4_RNN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16d1Xox0OW-VNuxDn1pvy2UXFIPfieCb9

# Recurrent Neural Networks

本次作業是要讓同學接觸 NLP 當中一個簡單的 task —— 語句分類（文本分類）

給定一個語句，判斷他有沒有惡意（負面標 1，正面標 0）

若有任何問題，歡迎來信至助教信箱 ntu-ml-2020spring-ta@googlegroups.com
"""

# from google.colab import drive
# drive.mount('/content/drive')
# path_prefix = 'drive/My Drive/Colab Notebooks/hw4 - Recurrent Neural Network'
from torch.nn.init import orthogonal
import sys
from sklearn.model_selection import train_test_split
from torch.utils import data
from gensim.models import Word2Vec
from torch import nn
from gensim.models import word2vec
import argparse
import os
import torch.nn.functional as F
import torch.optim as optim
import pandas as pd
import numpy as np
import torch
import warnings
path_prefix = './'
torch.manual_seed(0)
"""### Download Dataset
有三個檔案，分別是 training_label.txt、training_nolabel.txt、testing_data.txt

- training_label.txt：有 label 的 training data（句子配上 0 or 1，+++$+++ 只是分隔符號，不要理它）
    - e.g., 1 +++$+++ are wtf ... awww thanks !

- training_nolabel.txt：沒有 label 的 training data（只有句子），用來做 semi-supervised learning
    - ex: hates being this burnt !! ouch

- testing_data.txt：你要判斷 testing data 裡面的句子是 0 or 1

    >id,text

    >0,my dog ate our dinner . no , seriously ... he ate it .

    >1,omg last day sooon n of primary noooooo x im gona be swimming out of school wif the amount of tears am gona cry

    >2,stupid boys .. they ' re so .. stupid !
"""

# !wget --no-check-certificate 'https://drive.google.com/uc?export=download&id=1dPHIl8ZnfDz_fxNd2ZeBYedTat2lfxcO' -O 'drive/My Drive/Colab Notebooks/hw8-RNN/data/training_label.txt'
# !wget --no-check-certificate 'https://drive.google.com/uc?export=download&id=1x1rJOX_ETqnOZjdMAbEE2pqIjRNa8xcc' -O 'drive/My Drive/Colab Notebooks/hw8-RNN/data/training_nolabel.txt'
# !wget --no-check-certificate 'https://drive.google.com/uc?export=download&id=16CtnQwSDCob9xmm6EdHHR7PNFNiOrQ30' -O 'drive/My Drive/Colab Notebooks/hw8-RNN/data/testing_data.txt'

# this is for filtering the warnings
warnings.filterwarnings('ignore')

"""### Utils"""

# utils.py
# 這個 block 用來先定義一些等等常用到的函式


def load_training_data(path='training_label.txt'):
    # 把 training 時需要的 data 讀進來
    # 如果是 'training_label.txt'，需要讀取 label，如果是 'training_nolabel.txt'，不需要讀取 label
    if 'training_label' in path:
        with open(path, 'r') as f:
            lines = f.readlines()
            lines = [line.strip('\n').split(' ') for line in lines]
        x = [line[2:] for line in lines]
        y = [line[0] for line in lines]
        return x, y
    else:
        with open(path, 'r') as f:
            lines = f.readlines()
            x = [line.strip('\n').split(' ') for line in lines]
        return x


def load_testing_data(path='testing_data'):
    # 把 testing 時需要的 data 讀進來
    with open(path, 'r') as f:
        lines = f.readlines()
        X = ["".join(line.strip('\n').split(",")[1:]).strip()
             for line in lines[1:]]
        X = [sen.split(' ') for sen in X]
    return X


def evaluation(outputs, labels):
    # outputs => probability (float)
    # labels => labels
    outputs[outputs >= 0.5] = 1  # 大於等於 0.5 為有惡意
    outputs[outputs < 0.5] = 0  # 小於 0.5 為無惡意
    correct = torch.sum(torch.eq(outputs, labels)).item()
    return correct


"""### Train Word to Vector"""

# w2v.py
# 這個 block 是用來訓練 word to vector 的 word embedding
# 注意！這個 block 在訓練 word to vector 時是用 cpu，可能要花到 10 分鐘以上


def train_word2vec(x):
    # 訓練 word to vector 的 word embedding
    model = word2vec.Word2Vec(x, size=250, window=5,
                              min_count=5, workers=12, iter=10, sg=1)
    return model


"""### Data Preprocess"""

# preprocess.py
# 這個 block 用來做 data 的預處理


class Preprocess():
    def __init__(self, sentences, sen_len, w2v_path="./w2v.model"):
        self.w2v_path = w2v_path
        self.sentences = sentences
        self.sen_len = sen_len
        self.idx2word = []
        self.word2idx = {}
        self.embedding_matrix = []

    def get_w2v_model(self):
        # 把之前訓練好的 word to vec 模型讀進來
        self.embedding = Word2Vec.load(self.w2v_path)
        self.embedding_dim = self.embedding.vector_size

    def add_embedding(self, word):
        # 把 word 加進 embedding，並賦予他一個隨機生成的 representation vector
        # word 只會是 "<PAD>" 或 "<UNK>"
        vector = torch.empty(1, self.embedding_dim)
        torch.nn.init.uniform_(vector)
        self.word2idx[word] = len(self.word2idx)
        self.idx2word.append(word)
        self.embedding_matrix = torch.cat([self.embedding_matrix, vector], 0)

    def make_embedding(self, load=True):
        print("Get embedding ...")
        # 取得訓練好的 Word2vec word embedding
        if load:
            print("loading word to vec model ...")
            self.get_w2v_model()
        else:
            raise NotImplementedError
        # 製作一個 word2idx 的 dictionary
        # 製作一個 idx2word 的 list
        # 製作一個 word2vector 的 list
        for i, word in enumerate(self.embedding.wv.vocab):
            print('get words #{}'.format(i+1), end='\r')
            #e.g. self.word2index['he'] = 1
            #e.g. self.index2word[1] = 'he'
            # e.g. self.vectors[1] = 'he' vector
            self.word2idx[word] = len(self.word2idx)
            self.idx2word.append(word)
            self.embedding_matrix.append(self.embedding[word])
        print('')
        self.embedding_matrix = torch.tensor(self.embedding_matrix)
        # 將 "<PAD>" 跟 "<UNK>" 加進 embedding 裡面
        self.add_embedding("<PAD>")
        self.add_embedding("<UNK>")
        print("total words: {}".format(len(self.embedding_matrix)))
        return self.embedding_matrix

    def pad_sequence(self, sentence):
        # 將每個句子變成一樣的長度
        if len(sentence) > self.sen_len:
            sentence = sentence[:self.sen_len]
        else:
            pad_len = self.sen_len - len(sentence)
            for _ in range(pad_len):
                sentence.append(self.word2idx["<PAD>"])
        assert len(sentence) == self.sen_len
        return sentence

    def sentence_word2idx(self):
        # 把句子裡面的字轉成相對應的 index
        sentence_list = []
        for i, sen in enumerate(self.sentences):
            print('sentence count #{}'.format(i+1), end='\r')
            sentence_idx = []
            for word in sen:
                if (word in self.word2idx.keys()):
                    sentence_idx.append(self.word2idx[word])
                else:
                    sentence_idx.append(self.word2idx["<UNK>"])
            # 將每個句子變成一樣的長度
            sentence_idx = self.pad_sequence(sentence_idx)
            sentence_list.append(sentence_idx)
        return torch.LongTensor(sentence_list)

    def labels_to_tensor(self, y):
        # 把 labels 轉成 tensor
        y = [int(label) for label in y]
        return torch.LongTensor(y)


"""### Dataset"""

# data.py
# 實作了 dataset 所需要的 '__init__', '__getitem__', '__len__'
# 好讓 dataloader 能使用


class TwitterDataset(data.Dataset):
    """
    Expected data shape like:(data_num, data_len)
    Data can be a list of numpy array or a list of lists
    input data shape : (data_num, seq_len, feature_dim)

    __len__ will return the number of data
    """

    def __init__(self, X, y):
        self.data = X
        self.label = y

    def __getitem__(self, idx):
        if self.label is None:
            return self.data[idx]
        return self.data[idx], self.label[idx]

    def __len__(self):
        return len(self.data)


"""### Model"""

# model.py
# 這個 block 是要拿來訓練的模型


class LSTM_Net(nn.Module):
    def __init__(self, embedding, embedding_dim, hidden_dim, num_layers, dropout=0.5, fix_embedding=True, bi=False):
        super(LSTM_Net, self).__init__()
        # 製作 embedding layer
        self.embedding = torch.nn.Embedding(
            embedding.size(0), embedding.size(1))
        self.embedding.weight = torch.nn.Parameter(embedding)
        # 是否將 embedding fix 住，如果 fix_embedding 為 False，在訓練過程中，embedding 也會跟著被訓練
        self.embedding.weight.requires_grad = False if fix_embedding else True
        self.embedding_dim = embedding.size(1)
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        # LSTM output(sequence length, batch, hidden_dim*(1or2 依據有沒有bidirectional決定))
        # num_layers代表LSTM有幾層 一層就是會處理整個sequence length
        # h_n 會回傳每一層最後一個time step的hidden state(舊式投影片中的h)
        # c_n 會回傳每一層最後一個time step的 memory cell
        # for model1
        self.lstm = nn.GRU(embedding_dim, hidden_dim,
                           num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm2 = nn.GRU(hidden_dim*2, hidden_dim,
                            num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm3 = nn.GRU(hidden_dim*2, hidden_dim,
                            num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm4 = nn.GRU(hidden_dim*2, hidden_dim,
                            num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm5 = nn.GRU(hidden_dim*2, hidden_dim,
                            num_layers=1, batch_first=True, bidirectional=bi)
        for names in self.lstm._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm2._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm2, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm3._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm3, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm4._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm4, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm5._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm5, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        # for model 2
        self.lstm21 = nn.LSTM(embedding_dim, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm22 = nn.LSTM(hidden_dim*2, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm23 = nn.LSTM(hidden_dim*2, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi)
        for names in self.lstm21._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm21, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm22._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm22, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm23._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm23, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)

        # for model3
        self.lstm31 = nn.GRU(embedding_dim, hidden_dim*4,
                             num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm32 = nn.GRU(hidden_dim*8, hidden_dim*4,
                             num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm33 = nn.GRU(hidden_dim*8, hidden_dim,
                             num_layers=1, batch_first=True, bidirectional=bi)
        for names in self.lstm31._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm31, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm32._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm32, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm33._all_weights:

            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm33, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        # model4
        self.lstm41 = nn.GRU(embedding_dim, hidden_dim*5,
                             num_layers=1, batch_first=True, bidirectional=bi)
        self.lstm42 = nn.GRU(hidden_dim*10, hidden_dim,
                             num_layers=1, batch_first=True, bidirectional=bi)

        for names in self.lstm41._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm41, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm42._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm42, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        # for model5
        self.lstm51 = nn.LSTM(embedding_dim, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi, dropout=0.3)
        self.lstm52 = nn.LSTM(hidden_dim*2, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi, dropout=0.3)
        self.lstm53 = nn.LSTM(hidden_dim*2, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi, dropout=0.3)
        self.lstm54 = nn.LSTM(hidden_dim*2, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi, dropout=0.3)
        self.lstm55 = nn.LSTM(hidden_dim*2, hidden_dim,
                              num_layers=1, batch_first=True, bidirectional=bi)
        for names in self.lstm51._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm51, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm52._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm52, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm53._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm53, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm54._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm54, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)
        for names in self.lstm55._all_weights:
            for name in filter(lambda n: "bias" in n,  names):
                # filter返回names中有bias的部份形成的list
                # getattr把class self.lstm中的name屬性 回傳
                bias = getattr(self.lstm55, name)
                n = bias.size(0)
                # 因為bias_ih bias_hh的安排是(b_ii|b_if|b_ig|b_io|) 所以forget gate在n//4:n//2的地方
                start, end = n//4, n//2
                bias.data[start:end].fill_(1.)

        self.classifier = nn.Sequential(nn.Dropout(dropout),
                                        # bidirectional hidden要*2
                                        nn.Linear(hidden_dim*2, 1),
                                        nn.Sigmoid())
        self.classifier2 = nn.Sequential(nn.Dropout(dropout),
                                         # bidirectional hidden要*2
                                         nn.Linear(hidden_dim*2, 1),
                                         nn.Sigmoid())
        self.classifier3 = nn.Sequential(nn.Dropout(dropout),
                                         # bidirectional hidden要*2
                                         nn.Linear(hidden_dim*2, 1),
                                         nn.Sigmoid())
        self.classifier4 = nn.Sequential(nn.Dropout(dropout),
                                         # bidirectional hidden要*2
                                         nn.Linear(hidden_dim*2, 1),
                                         nn.Sigmoid())
        self.classifier5 = nn.Sequential(nn.Dropout(dropout),
                                         # bidirectional hidden要*2
                                         nn.Linear(hidden_dim*2, 1),
                                         nn.Sigmoid())

    def layer_normalization(self, hidden_state):
        # (batch, sequence, hidden_dim)
        # 分兩層 所以分開處理
        size = len(hidden_state[0][0])//2
        h_for_mean = torch.mean(hidden_state[:, :, :size], dim=2)
        h_for_std = torch.std(hidden_state[:, :, :size], dim=2)
        h_back_mean = torch.mean(hidden_state[:, :, size:], dim=2)
        h_back_std = torch.std(hidden_state[:, :, size:], dim=2)
        return torch.cat([(hidden_state[:, :, :size]-h_for_mean[:, :, None])/(h_for_std[:, :, None]),
                          (hidden_state[:, :, size:]-h_back_mean[:, :, None])/(h_back_std[:, :, None])], dim=2)

    def forward(self, inputs):
        inputs = self.embedding(inputs)
        # for model1
        h1, _ = self.lstm(inputs, None)
        h1 = self.layer_normalization(h1)

        h2, _ = self.lstm2(h1, None)
        h2 = self.layer_normalization(h2)

        h3, _ = self.lstm3(h2, None)
        h3 = self.layer_normalization(h3)

        h4, _ = self.lstm4(h3, None)
        h4 = self.layer_normalization(h4)

        x1, _ = self.lstm5(h4, None)

        x1 = x1[:, -1, :]
        # for model2
        h21, _ = self.lstm21(inputs, None)
        h21 = self.layer_normalization(h21)

        h22, _ = self.lstm22(h21, None)
        h22 = self.layer_normalization(h22)

        x2, _ = self.lstm23(h22, None)
        x2 = self.layer_normalization(x2)
        x2 = x2[:, -1, :]
        # for model3
        h31, _ = self.lstm31(inputs, None)
        h31 = self.layer_normalization(h31)

        h32, _ = self.lstm32(h31, None)
        h32 = self.layer_normalization(h32)

        x3, _ = self.lstm33(h32, None)
        x3 = self.layer_normalization(x3)
        x3 = x3[:, -1, :]
        # for model4
        h41, _ = self.lstm41(inputs, None)
        h41 = self.layer_normalization(h41)

        x4, _ = self.lstm42(h41, None)
        x4 = self.layer_normalization(x4)

        x4 = x4[:, -1, :]
        # for model 5
        h51, _ = self.lstm51(inputs, None)
        h51 = self.layer_normalization(h51)

        h52, _ = self.lstm52(h51, None)
        h52 = self.layer_normalization(h52)

        h53, _ = self.lstm53(h52, None)
        h53 = self.layer_normalization(h53)

        h54, _ = self.lstm54(h53, None)
        h54 = self.layer_normalization(h54)

        x5, _ = self.lstm55(h54, None)

        x5 = x5[:, -1, :]
        # x 的 dimension (batch, seq_len, hidden_size)
        # 取用 LSTM 最後一層的 hidden state

        x1 = self.classifier(x1)
        x2 = self.classifier2(x2)
        x3 = self.classifier3(x3)
        x4 = self.classifier4(x4)
        x5 = self.classifier5(x5)
        # x = (x1+x2+x3)/3
        # 這裡有改
        return x1, x2, x3, x4, x5


"""### Train"""

# train.py
# 這個 block 是用來訓練模型的


def training(batch_size, n_epoch, lr, model_dir, train, valid, model, device):
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print('\nstart training, parameter total:{}, trainable:{}\n'.format(
        total, trainable))
    model.train()  # 將 model 的模式設為 train，這樣 optimizer 就可以更新 model 的參數
    criterion = nn.BCELoss()  # 定義損失函數，這裡我們使用 binary cross entropy loss
    t_batch = len(train)
    v_batch = len(valid)
    # 將模型的參數給 optimizer，並給予適當的 learning rate
    optimizer = optim.Adam(model.parameters(), lr=lr)
    total_loss, total_acc, best_acc = 0, 0, 0
    for epoch in range(n_epoch):
        total_loss, total_acc = 0, 0
        # 這段做 training
        for i, (inputs, labels) in enumerate(train):
            # device 為 "cuda"，將 inputs 轉成 torch.cuda.LongTensor
            inputs = inputs.to(device, dtype=torch.long)
            # device為 "cuda"，將 labels 轉成 torch.cuda.FloatTensor，因為等等要餵進 criterion，所以型態要是 float
            labels = labels.to(device, dtype=torch.float)
            optimizer.zero_grad()  # 由於 loss.backward() 的 gradient 會累加，所以每次餵完一個 batch 後需要歸零
            # 同時train三個model
            outputs, outputs2, outputs3, outputs4, outputs5 = model(
                inputs)  # 將 input 餵給模型
            outputs = outputs.squeeze()  # 去掉最外面的 dimension，好讓 outputs 可以餵進 criterion()
            outputs2 = outputs2.squeeze()
            outputs3 = outputs3.squeeze()
            outputs4 = outputs4.squeeze()
            outputs5 = outputs5.squeeze()

            optimizer.zero_grad()  # 由於 loss.backward() 的 gradient 會累加，所以每次餵完一個 batch 後需要歸零
            loss = criterion(outputs, labels)  # 計算此時模型的 training loss
            loss.backward()  # 算 loss 的 gradient
            optimizer.step()  # 更新訓練模型的參數

            optimizer.zero_grad()
            loss = criterion(outputs2, labels)  # 計算此時模型的 training loss
            loss.backward()  # 算 loss 的 gradient
            optimizer.step()  # 更新訓練模型的參數

            optimizer.zero_grad()
            loss = criterion(outputs3, labels)  # 計算此時模型的 training loss
            loss.backward()  # 算 loss 的 gradient
            optimizer.step()  # 更新訓練模型的參數

            optimizer.zero_grad()
            loss = criterion(outputs4, labels)  # 計算此時模型的 training loss
            loss.backward()  # 算 loss 的 gradient
            optimizer.step()  # 更新訓練模型的參數

            optimizer.zero_grad()
            loss = criterion(outputs5, labels)  # 計算此時模型的 training loss
            loss.backward()  # 算 loss 的 gradient
            optimizer.step()  # 更新訓練模型的參數
            # 計算此時模型的 training accuracy
            correct = evaluation(
                (outputs+outputs2+outputs3+outputs4+outputs5)/5, labels)
            total_acc += (correct / batch_size)
            total_loss += loss.item()
            print('[ Epoch{}: {}/{} ] loss:{:.3f} acc:{:.3f} '.format(
                epoch+1, i+1, t_batch, loss.item(), correct*100/batch_size), end='\r')
        print('\nTrain | Loss:{:.5f} Acc: {:.3f}'.format(
            total_loss/t_batch, total_acc/t_batch*100))

        # 這段做 validation
        model.eval()  # 將 model 的模式設為 eval，這樣 model 的參數就會固定住

        torch.save(model, "{}/ckpt.model".format(model_dir))
        print('saving model with acc {:.3f}'.format(
            total_acc/v_batch*100))
        print('-----------------------------------------------')
        model.train()  # 將 model 的模式設為 train，這樣 optimizer 就可以更新 model 的參數（因為剛剛轉成 eval 模式）


"""### Test"""

# test.py
# 這個 block 用來對 testing_data.txt 做預測


def testing(batch_size, test_loader, model, device):
    model.eval()
    ret_output = []
    with torch.no_grad():
        for i, inputs in enumerate(test_loader):
            inputs = inputs.to(device, dtype=torch.long)
            outputs1, outputs2, outputs3, outputs4, outputs5 = model(inputs)
            # 這裡有改
            outputs = (outputs1+outputs2+outputs3+outputs4+outputs5)/5
            outputs[outputs >= 0.5] = 1  # 大於等於 0.5 為負面
            outputs[outputs < 0.5] = 0  # 小於 0.5 為正面
            outputs = outputs.reshape(-1)
            ret_output += outputs.int().tolist()
        print(outputs.size())
    return ret_output


"""### Main"""

# main.py

# 通過 torch.cuda.is_available() 的回傳值進行判斷是否有使用 GPU 的環境，如果有的話 device 就設為 "cuda"，沒有的話就設為 "cpu"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 處理好各個 data 的路徑
# train_with_label = sys.argv[1]
# train_no_label = sys.argv[2]
testing_data = sys.argv[1]

# 處理 word to vec model 的路徑
w2v_path = os.path.join(path_prefix, './w2v_all.model')

# 定義句子長度、要不要固定 embedding、batch 大小、要訓練幾個 epoch、learning rate 的值、model 的資料夾路徑
sen_len = 26
fix_embedding = True  # fix embedding during training
batch_size = 128
epoch = 13
lr = 0.001
w2v_vector_dim = 200
# model_dir = os.path.join(path_prefix, 'model/') # model directory for checkpoint model
model_dir = path_prefix  # model directory for checkpoint model

print("loading data ...")  # 把 'training_label.txt' 跟 'training_nolabel.txt' 讀進來
# train_x, y = load_training_data(train_with_label)
# train_x_no_label = load_training_data(train_no_label)

# 對 input 跟 labels 做預處理
# preprocess = Preprocess(train_x, sen_len, w2v_path=w2v_path)
# embedding = preprocess.make_embedding(load=True)
# train_x = preprocess.sentence_word2idx()
# y = preprocess.labels_to_tensor(y)

# 製作一個 model 的對象

model = LSTM_Net(embedding, embedding_dim=w2v_vector_dim, hidden_dim=50,
                 num_layers=5, dropout=0.5, fix_embedding=fix_embedding, bi=True)
# device為 "cuda"，model 使用 GPU 來訓練（餵進去的 inputs 也需要是 cuda tensor）
model = model.to(device)

# 把 data 分為 training data 跟 validation data（將一部份 training data 拿去當作 validation data）
# X_train, X_val, y_train, y_val = train_x[:
#                                          ], train_x[180000:], y[:], y[180000:]

# 把 data 做成 dataset 供 dataloader 取用
# train_dataset = TwitterDataset(X=X_train, y=y_train)
# val_dataset = TwitterDataset(X=X_val, y=y_val)

# 把 data 轉成 batch of tensors
# train_loader = torch.utils.data.DataLoader(dataset=train_dataset,
#                                            batch_size=batch_size,
#                                            shuffle=True,
#                                            num_workers=8)

# val_loader = torch.utils.data.DataLoader(dataset=val_dataset,
#                                          batch_size=batch_size,
#                                          shuffle=False,
#                                          num_workers=8)

# # 開始訓練
# training(batch_size, epoch, lr, model_dir,
#          train_loader, val_loader, model, device)

"""### Predict and Write to csv file"""

# 開始測試模型並做預測
print("loading testing data ...")
test_x = load_testing_data(testing_data)
preprocess = Preprocess(test_x, sen_len, w2v_path=w2v_path)
embedding = preprocess.make_embedding(load=True)
test_x = preprocess.sentence_word2idx()
test_dataset = TwitterDataset(X=test_x, y=None)
test_loader = torch.utils.data.DataLoader(dataset=test_dataset,
                                          batch_size=batch_size,
                                          shuffle=False,
                                          num_workers=8)
print('\nload model ...')
model = torch.load(os.path.join(model_dir, 'ckpt.model'))
outputs = testing(batch_size, test_loader, model, device)

# 寫到 csv 檔案供上傳 Kaggle
tmp = pd.DataFrame({"id": [str(i)
                           for i in range(len(test_x))], "label": outputs})
print("save csv ...")
tmp.to_csv(sys.argv[2], index=False)
print("Finish Predicting")
