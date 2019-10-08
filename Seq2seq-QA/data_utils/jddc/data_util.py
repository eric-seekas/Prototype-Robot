#coding=utf-8
import pandas as pd
from itertools import chain
import nltk
from tqdm import tqdm
import numpy as np
import random
import os
import string
import pickle

class Batch:
    """Struct containing batches info
    """
    def __init__(self):
        self.encoderSeqs = []
        self.decoderSeqs = []
        self.targetSeqs = []
        self.weights = []


class TextData:

    def __init__(self, args):

        self.args = args

        self.sr_word2id = None
        self.sr_id2word = None
        self.sr_line_id = None

        self.train_samples = []  # train samples with id

        self.padToken = "<pad>"  # Padding
        self.goToken = "<go>"  # Start of sequence
        self.eosToken = "<eos>"  # End of sequence
        self.unknownToken = "<unk>"  # Word dropped from vocabulary
        self.numToken = 4 # Num of above Tokens

        self.load_data()
        self.build_word_dict()
        self.generate_conversations()

        # generate batches
        self.batch_index = 0
        self.epoch_completed = 0


    def load_data(self):
        #if not os.path.exists(self.args.sr_word_id_path) or not os.path.exists(self.args.train_samples_path):
        if True:
            # 读取 movie_lines.txt 和movie_conversations.txt两个文件
            print("开始读取数据")
            self.lines = pd.read_csv(self.args.line_path, sep="\t",
                                     usecols=[0,2,6],
                                     names=["session_id","speaker_flag","utterance"],
                                     dtype={'utterance':str})
            # 进行分词操作，暂时屏蔽
            # self.lines.utterance = self.lines.utterance.apply(lambda conv : self.word_tokenizer(conv))

            print("当前数据", self.lines[:10])
            print("当前数据", self.lines.utterance[:10])
            print("数据读取完毕")

    def build_word_dict(self):
        if not os.path.exists(self.args.sr_word_id_path):
            # 得到word2id和id2word两个词典
            print("开始构建词典")
            words = self.lines.utterance.values
            words = [str(item) for item in words]
            print(len(words))
            #words = list(chain(*words))
            # 将全部words转为小写
            print("正在转为小写")
            words = list(map(str.lower, words))
            print("转化小写完毕")

            sr_words_count = pd.Series(words).value_counts()
            # 筛选出 出现次数 大于 1 的词作为 vocabulary
            #sr_words_size = np.where(sr_words_count.values > self.args.vacab_filter)[0].size
            sr_words_size = np.where(sr_words_count.values > 0)[0].size
            sr_words_index = sr_words_count.index[0:sr_words_size]

            self.sr_word2id = pd.Series(range(self.numToken, self.numToken + sr_words_size), index=sr_words_index)
            self.sr_id2word = pd.Series(sr_words_index, index=range(self.numToken, self.numToken + sr_words_size))
            self.sr_word2id[self.padToken] = 0
            self.sr_word2id[self.goToken] = 1
            self.sr_word2id[self.eosToken] = 2
            self.sr_word2id[self.unknownToken] = 3
            self.sr_id2word[0] = self.padToken
            self.sr_id2word[1] = self.goToken
            self.sr_id2word[2] = self.eosToken
            self.sr_id2word[3] = self.unknownToken
            print(self.sr_id2word)
            print("词典构建完毕")
            with open(os.path.join(self.args.sr_word_id_path), 'wb') as handle:
                data = {
                    'word2id': self.sr_word2id,
                    'id2word': self.sr_id2word,
                }
                pickle.dump(data, handle, -1)
        else:
            print(self.sr_id2word)
            print("从{}载入词典".format(self.args.sr_word_id_path))
            with open(self.args.sr_word_id_path, 'rb') as handle:
                data = pickle.load(handle)
                self.sr_word2id = data['word2id']
                self.sr_id2word = data['id2word']

    def replace_word_with_id(self, conv):
        conv = list(map(str.lower, conv))
        conv = list(map(self.get_word_id, conv))
        # temp = list(map(self.get_id_word, conv))
        return conv

    def get_word_id(self, word):
        if word in self.sr_word2id:
            return self.sr_word2id[word]
        else:
            return self.sr_word2id[self.unknownToken]

    def get_id_word(self, id):
        if id in self.sr_id2word:
            return self.sr_id2word[id]
        else:
            return self.unknownToken

    def generate_conversations(self):

        if not os.path.exists(self.args.train_samples_path):
            # 将word替换为id
            # self.replace_word_with_id()
            print("开始生成训练样本")
            # 将id与line作为字典，以方便生成训练样本
           
            session_list = []
            speaker_list = []
            utterance_list = []

            count = 0

            print("self.lines in make conversation \n", self.lines)
            print("length", len(self.lines.session_id.values))

            for tmp_session_id, tmp_speaker_id, tmp_utterance in zip(self.lines.session_id.values, self.lines.speaker_flag.values, self.lines.utterance.values): 
                print("count", count)
                count = count + 1
                if count < len(self.lines.session_id.values):
                    next_session_id = self.lines.session_id.values[count]
                    next_speaker_id = self.lines.speaker_flag.values[count]
                    
                if tmp_session_id == next_session_id:
                    # 继续当前session，生成speaker_list
                    utterance_list.append(tmp_utterance)
                    if tmp_speaker_id == next_speaker_id:
                        # 当前行 和 下一行 是同一个说话的人
                        pass
                    else:
                        # 当前行 和 下一行 不是同一个说话的人
                        speaker_list.append(utterance_list.copy())
                        utterance_list = []

                else:
                    # 当前session 结束
                    print("tmp_session_id", tmp_session_id)
                    print("next_session_id", next_session_id)
                    
                    print("tmp_speaker_id", tmp_speaker_id)
                    print("next_speaker_id", next_speaker_id)
                    
                    print("speaker list", speaker_list)
                    # 当前session 结束, 遍历speaker_list,
                    # 生产conversation，speaker_list 清空

                    for idx in range(len(speaker_list) - 1):
                        first_conv = "".join(speaker_list[idx]).strip('"[]')
                        print('first conv', first_conv)
                        second_conv = "".join(speaker_list[idx + 1])
                        print('second conv', second_conv)
                        valid = self.filter_conversations(first_conv, second_conv)
                        if valid:
                            temp = [first_conv, second_conv]
                            print("sample", temp)
                            self.train_samples.append(temp)

            print("生成训练样本结束")
            with open(self.args.train_samples_path, 'wb') as handle:
                data = {
                    'train_samples': self.train_samples
                }
                pickle.dump(data, handle, -1)
        else:
            with open(self.args.train_samples_path, 'rb') as handle:
                data = pickle.load(handle)
                self.train_samples = data['train_samples']
            print("从{}导入训练样本".format(self.args.train_samples_path))

    def word_tokenizer(self, sentence):
        # 英文分词
        words = nltk.word_tokenize(str(sentence))
        return words

    def filter_conversations(self, first_conv, second_conv):
        # 筛选样本， 首先将encoder_input 或 decoder_input大于max_length的conversation过滤
        # 其次将target中包含有UNK的conversation过滤
        valid = True
        #valid &= len(str(first_conv)) <= self.args.maxLength
        #valid &= len(str(second_conv)) <= self.args.maxLength
        #alid &= list(second_conv).count(self.sr_word2id[self.unknownToken]) == 0

        return valid

    def get_next_batches(self):
        """Prepare the batches for the current epoch
        Return:
            list<Batch>: Get a list of the batches for the next epoch
        """
        # self.shuffle()

        batches = []

        def gen_next_samples():
            """ Generator over the mini-batch training samples
            """
            for i in range(0, len(self.train_samples), self.args.batch_size):
                yield self.train_samples[i:min(i + self.args.batch_size, len(self.train_samples))]

        # TODO: Should replace that by generator (better: by tf.queue)

        for samples in gen_next_samples():
            batch = self.create_batch(samples)
            batches.append(batch)
        return batches

    def shuffle(self):
        """Shuffle the training samples
        """
        print('Shuffling the dataset...')
        random.shuffle(self.train_samples)

    def create_batch(self, samples):
        batch = Batch()
        batch_size = len(samples)

        print("samples", samples)

        # Create the batch tensor
        for i in range(batch_size):
            # Unpack the sample
            sample = samples[i]
            print('sample', sample)
            print('sample 0', sample[0])
            batch.encoderSeqs.append([self.sr_word2id[item] for item in list(reversed(sample[0]) if item in self.word2id.keys() else 3 )])  # Reverse inputs (and not outputs), little trick as defined on the original seq2seq paper
            print('sample 1', sample[1])
            batch.decoderSeqs.append([self.sr_word2id[self.goToken]] + [self.sr_word2id[item] for item in list(sample[1]) if item in self.word2id.keys() else 3] + [self.sr_word2id[self.eosToken]])  # Add the <go> and <eos> tokens
            batch.targetSeqs.append(batch.decoderSeqs[-1][1:])  # Same as decoder, but shifted to the left (ignore the <go>)

            # Long sentences should have been filtered during the dataset creation
            #assert len(batch.encoderSeqs[i]) <= self.args.maxLengthEnco
            #assert len(batch.decoderSeqs[i]) <= self.args.maxLengthDeco

            # TODO: Should use tf batch function to automatically add padding and batch samples
            # Add padding & define weight
            batch.encoderSeqs[i] = [self.sr_word2id[self.padToken]] * (self.args.maxLengthEnco - len(batch.encoderSeqs[i])) + batch.encoderSeqs[i]  # Left padding for the input
            batch.weights.append([1.0] * len(batch.targetSeqs[i]) + [0.0] * (self.args.maxLengthDeco - len(batch.targetSeqs[i])))
            batch.decoderSeqs[i] = batch.decoderSeqs[i] + [self.sr_word2id[self.padToken]] * (self.args.maxLengthDeco - len(batch.decoderSeqs[i]))
            batch.targetSeqs[i] = batch.targetSeqs[i] + [self.sr_word2id[self.padToken]] * (self.args.maxLengthDeco - len(batch.targetSeqs[i]))

        # Simple hack to reshape the batch
        encoderSeqsT = []  # Corrected orientation
        for i in range(self.args.maxLengthEnco):
            encoderSeqT = []
            for j in range(batch_size):
                encoderSeqT.append(batch.encoderSeqs[j][i])
            encoderSeqsT.append(encoderSeqT)
        batch.encoderSeqs = encoderSeqsT

        decoderSeqsT = []
        targetSeqsT = []
        weightsT = []
        for i in range(self.args.maxLengthDeco):
            decoderSeqT = []
            targetSeqT = []
            weightT = []
            for j in range(batch_size):
                decoderSeqT.append(batch.decoderSeqs[j][i])
                targetSeqT.append(batch.targetSeqs[j][i])
                weightT.append(batch.weights[j][i])
            decoderSeqsT.append(decoderSeqT)
            targetSeqsT.append(targetSeqT)
            weightsT.append(weightT)
        batch.decoderSeqs = decoderSeqsT
        batch.targetSeqs = targetSeqsT
        batch.weights = weightsT

        return batch

    def sentence2enco(self, sentence):
        """Encode a sequence and return a batch as an input for the model
        Return:
            Batch: a batch object containing the sentence, or none if something went wrong
        """

        if sentence == '':
            return None

        # First step: Divide the sentence in token
        tokens = nltk.word_tokenize(sentence)
        print('tokens', tokens)
        if len(tokens) > self.args.maxLength:
            return None

        # Second step: Convert the token in word ids
        wordIds = []
        for token in tokens:
            if token in self.sr_word2id:
                wordIds.append(self.sr_word2id[token])  # Create the vocabulary and the training sentences
            else:
                wordIds.append(self.sr_word2id[self.unknownToken])
                # Third step: creating the batch (add padding, reverse)
        batch = self.create_batch([[wordIds, []]])  # Mono batch, no target output

        return batch

    def deco2sentence(self, decoderOutputs):
        """Decode the output of the decoder and return a human friendly sentence
        decoderOutputs (list<np.array>):
        """
        sequence = []

        # Choose the words with the highest prediction score
        for out in decoderOutputs:
            sequence.append(np.argmax(out))  # Adding each predicted word ids

        return sequence

    def sequence2str(self, sequence, clean=False, reverse=False):
        """Convert a list of integer into a human readable string
        Args:
            sequence (list<int>): the sentence to print
            clean (Bool): if set, remove the <go>, <pad> and <eos> tokens
            reverse (Bool): for the input, option to restore the standard order
        Return:
            str: the sentence
        """

        if not sequence:
            return ''

        if not clean:
            return ' '.join([self.sr_id2word[idx] for idx in sequence])

        sentence = []
        for wordId in sequence:
            if wordId == self.sr_word2id[self.eosToken]:  # End of generated sentence
                break
            elif wordId != self.padToken and wordId != self.goToken:
                sentence.append(self.sr_id2word[wordId])

        if reverse:  # Reverse means input so no <eos> (otherwise pb with previous early stop)
            sentence.reverse()

        return self.detokenize(sentence)

    def detokenize(self, tokens):
        """Slightly cleaner version of joining with spaces.
        Args:
            tokens (list<string>): the sentence to print
        Return:
            str: the sentence
        """
        return ''.join([' ' + t if not t.startswith('\'') and t not in string.punctuation else t for t in tokens]).strip().capitalize()


if __name__ == '__main__':
    class args:
        def __init__(self):
            self.line_path = "../../data/jddc/chat_simple.txt"
            self.sr_word_id_path = "../../data/jddc/word_id.txt"
            self.train_samples_path = "../../data/jddc/train_sample.txt"
            self.maxLength = 512
    args = args()
    textData = TextData(args)
