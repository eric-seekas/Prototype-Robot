# coding:utf-8

import sys
import numpy as np
import tensorflow as tf
from tensorflow.contrib.legacy_seq2seq.python.ops import seq2seq
import word_token
import jieba
import random


"""
参数配置，根据自己的业务场景和需求调整
"""

# 输入序列长度
input_seq_len = 50
# 输出序列长度
output_seq_len = 50
# 空值填充0
PAD_ID = 0
# 输出序列起始标记
GO_ID = 1
# 结尾标记
EOS_ID = 2
# LSTM神经元size
size = 8
# 初始学习率
init_learning_rate = 1
# 在样本中出现频率超过这个值才会进入词表
min_freq = 10

# 训练的轮数
train_round = 50

wordToken = word_token.WordToken()

# 放在全局的位置，为了动态算出num_encoder_symbols和num_decoder_symbols
max_token_id = wordToken.load_file_list(['samples/question.txt', 'samples/answer.txt'], min_freq)
num_encoder_symbols = max_token_id + 5 #表示encoder_inputs中的整数词id的数目
num_decoder_symbols = max_token_id + 5


def get_id_list_from(sentence):
    """
    获取输入句子的分词对应id列表
    """
    sentence_id_list = []
    seg_list = jieba.cut(sentence)
    for str in seg_list:
        id = wordToken.word2id(str)
        if id:
            sentence_id_list.append(wordToken.word2id(str))
    return sentence_id_list


def get_train_set():
    """
    获取问答语句，并处理成id list：[[question_id_list,answer_id_list]]
    """
    global num_encoder_symbols, num_decoder_symbols
    train_set = []
    with open('samples/question.txt', 'r',encoding='utf-8') as question_file:
        with open('samples/answer.txt', 'r',encoding='utf-8') as answer_file:
            while True:
                question = question_file.readline()
                answer = answer_file.readline()
                if question and answer:
                    question = question.strip()
                    answer = answer.strip()

                    question_id_list = get_id_list_from(question)
                    answer_id_list = get_id_list_from(answer)
                    if len(question_id_list) > 0 and len(answer_id_list) > 0:
                        answer_id_list.append(EOS_ID) # 添加 EOS_ID
                        train_set.append([question_id_list, answer_id_list])
                else:
                    break
    return train_set


def get_samples(train_set, batch_num):
    """
    构造样本数据

    :return:
        encoder_inputs: [array([0, 0], dtype=int32), array([0, 0], dtype=int32), array([5, 5], dtype=int32),
                        array([7, 7], dtype=int32), array([9, 9], dtype=int32)]
        decoder_inputs: [array([1, 1], dtype=int32), array([11, 11], dtype=int32), array([13, 13], dtype=int32),
                        array([15, 15], dtype=int32), array([2, 2], dtype=int32)]
        哥要解释一下：encoder_input:5维列表(Tensor),表示一句话是5个词，每次词是一个长度为2的array(tensor),表示batch=2，batch1的input
        的这句话为[0,0,5,7,9]每个整数表示词id.decoder_inputs同理可得.
    """
    # train_set = [[[5, 7, 9], [11, 13, 15, EOS_ID]], [[7, 9, 11], [13, 15, 17, EOS_ID]], [[15, 17, 19], [21, 23, 25, EOS_ID]]]
    raw_encoder_input = []
    raw_decoder_input = []
    if batch_num >= len(train_set):
        batch_train_set = train_set
    else:
        random_start = random.randint(0, len(train_set)-batch_num)
        batch_train_set = train_set[random_start:random_start+batch_num]
    for sample in batch_train_set: # PADDING
        raw_encoder_input.append([PAD_ID] * (input_seq_len - len(sample[0])) + sample[0])
        raw_decoder_input.append([GO_ID] + sample[1] + [PAD_ID] * (output_seq_len - len(sample[1]) - 1)) # GO_ID

    encoder_inputs = []
    decoder_inputs = []
    target_weights = []

    for length_idx in range(input_seq_len):
        encoder_inputs.append(np.array([encoder_input[length_idx] for encoder_input in raw_encoder_input], dtype=np.int32))
    for length_idx in range(output_seq_len):
        decoder_inputs.append(np.array([decoder_input[length_idx] for decoder_input in raw_decoder_input], dtype=np.int32))
        target_weights.append(np.array([0.0 if length_idx == output_seq_len - 1 or decoder_input[length_idx] == PAD_ID else 1.0 for decoder_input in raw_decoder_input], dtype=np.float32))
    return encoder_inputs, decoder_inputs, target_weights


def seq_to_encoder(input_seq):
    """
    从输入空格分隔的数字id串，转成预测用的encoder、decoder、target_weight等
    """
    input_seq_array = [int(v) for v in input_seq.split()]
    encoder_input = [PAD_ID] * (input_seq_len - len(input_seq_array)) + input_seq_array
    decoder_input = [GO_ID] + [PAD_ID] * (output_seq_len - 1)
    encoder_inputs = [np.array([v], dtype=np.int32) for v in encoder_input]
    decoder_inputs = [np.array([v], dtype=np.int32) for v in decoder_input]
    target_weights = [np.array([1.0], dtype=np.float32)] * output_seq_len
    return encoder_inputs, decoder_inputs, target_weights


def get_model(feed_previous=False):
    """
    构造模型:seq2seq
    feed_previous表示decoder_inputs是我们直接提供训练数据的输入，
    还是用前一个RNNCell的输出映射出来的，如果feed_previous为True，
    那么就是用前一个RNNCell的输出，并经过Wx+b线性变换成
    """

    learning_rate = tf.Variable(float(init_learning_rate), trainable=False, dtype=tf.float32)
    learning_rate_decay_op = learning_rate.assign(learning_rate * 0.9)

    encoder_inputs = []
    decoder_inputs = []
    target_weights = []
    for i in range(input_seq_len):
        encoder_inputs.append(tf.placeholder(tf.int32, shape=[None], name="encoder{0}".format(i)))
    for i in range(output_seq_len + 1):
        decoder_inputs.append(tf.placeholder(tf.int32, shape=[None], name="decoder{0}".format(i)))
    for i in range(output_seq_len):
        target_weights.append(tf.placeholder(tf.float32, shape=[None], name="weight{0}".format(i)))

    # decoder_inputs左移一个时序作为targets
    targets = [decoder_inputs[i + 1] for i in range(output_seq_len)]

    cell = tf.contrib.rnn.BasicLSTMCell(size)

    # 这里输出的状态我们不需要
    outputs, _ = seq2seq.embedding_attention_seq2seq(
                        encoder_inputs,
                        decoder_inputs[:output_seq_len],
                        cell,
                        num_encoder_symbols=num_encoder_symbols,
                        num_decoder_symbols=num_decoder_symbols,
                        embedding_size=size,
                        output_projection=None,
                        feed_previous=feed_previous,
                        dtype=tf.float32)

    # 计算加权交叉熵损失
    loss = seq2seq.sequence_loss(outputs, targets, target_weights)
    # 梯度下降优化器
    opt = tf.train.GradientDescentOptimizer(learning_rate)
    # 优化目标：让loss最小化
    update = opt.apply_gradients(opt.compute_gradients(loss))
    # 模型持久化
    saver = tf.train.Saver(tf.global_variables())

    return encoder_inputs, decoder_inputs, target_weights, outputs, loss, update, saver, learning_rate_decay_op, learning_rate


def train():
    """
    训练过程
    """
    # train_set = [[[5, 7, 9], [11, 13, 15, EOS_ID]], [[7, 9, 11], [13, 15, 17, EOS_ID]],
    #              [[15, 17, 19], [21, 23, 25, EOS_ID]]]
    train_set = get_train_set()
    with tf.Session() as sess:

        encoder_inputs, decoder_inputs, target_weights, outputs, loss, update, saver, learning_rate_decay_op, learning_rate = get_model()

        # 全部变量初始化
        sess.run(tf.global_variables_initializer())

        # 训练很多次迭代，每隔10次打印一次loss，可以看情况直接ctrl+c停止
        previous_losses = []
        for step in range(train_round):
            sample_encoder_inputs, sample_decoder_inputs, sample_target_weights = get_samples(train_set, 1000)
            input_feed = {}
            for l in range(input_seq_len):
                input_feed[encoder_inputs[l].name] = sample_encoder_inputs[l]
            for l in range(output_seq_len):
                input_feed[decoder_inputs[l].name] = sample_decoder_inputs[l]
                input_feed[target_weights[l].name] = sample_target_weights[l]
            input_feed[decoder_inputs[output_seq_len].name] = np.zeros([len(sample_decoder_inputs[0])], dtype=np.int32)
            [loss_ret, _] = sess.run([loss, update], input_feed)
            if step % 10 == 0:
                print('[+]step='+str(step)+',loss='+str(loss_ret)+',learning_rate='+str(learning_rate.eval()))
                with open('lx_bot_v3.log', 'a') as my_logger: 
                    my_logger.write('[+]step='+str(step)+',loss='+str(loss_ret)+',learning_rate='+str(learning_rate.eval())+'\n')

                if len(previous_losses) > 5 and loss_ret > max(previous_losses[-5:]):
                    sess.run(learning_rate_decay_op)
                previous_losses.append(loss_ret)

                # 模型持久化
                saver.save(sess, 'model/lx_bot_v3')


def predict():
    """
    预测过程
    """
    with tf.Session() as sess:
        encoder_inputs, decoder_inputs, target_weights, outputs, loss, update, saver, learning_rate_decay_op, learning_rate = get_model(feed_previous=True)
        saver.restore(sess, 'model/lx_bot_v3')
        sys.stdout.write("[in:]")
        sys.stdout.flush()
        input_seq = sys.stdin.readline()
        while input_seq:
            input_seq = input_seq.strip()
            input_id_list = get_id_list_from(input_seq)
            if (len(input_id_list)):
                sample_encoder_inputs, sample_decoder_inputs, sample_target_weights = seq_to_encoder(' '.join([str(v) for v in input_id_list]))

                input_feed = {}
                for l in range(input_seq_len):
                    input_feed[encoder_inputs[l].name] = sample_encoder_inputs[l]
                for l in range(output_seq_len):
                    input_feed[decoder_inputs[l].name] = sample_decoder_inputs[l]
                    input_feed[target_weights[l].name] = sample_target_weights[l]
                input_feed[decoder_inputs[output_seq_len].name] = np.zeros([2], dtype=np.int32)

                # 预测输出
                outputs_seq = sess.run(outputs, input_feed)
                # 因为输出数据每一个是num_decoder_symbols维的，因此找到数值最大的那个就是预测的id，就是这里的argmax函数的功能
                outputs_seq = [int(np.argmax(logit[0], axis=0)) for logit in outputs_seq]
                # 如果是结尾符，那么后面的语句就不输出了
                if EOS_ID in outputs_seq:
                    outputs_seq = outputs_seq[:outputs_seq.index(EOS_ID)]
                outputs_seq = [wordToken.id2word(v) for v in outputs_seq]
                print(str(" ".join(outputs_seq)))
                little_x_say = str(" ".join(outputs_seq))
            else:
                print("你的智商好高啊，这个问题小X回答不了") #这个位置可以换成兜底话术
                little_x_say = str("你的智商好高啊，这个问题小X回答不了")

            return little_x_say

            #sys.stdout.write("[in:]")
            sys.stdout.flush()
            input_seq = sys.stdin.readline()


import datetime
if __name__ == "__main__":
    start = datetime.datetime.now()
    if sys.argv[1] == 'train':
        train()
    else:
        predict()
    end = datetime.datetime.now()
    print("训练{0}轮模型，需要时间约{1}分钟".format(str(train_round),str((end-start).seconds/60.0)))
    with open('lx_bot_v3.log', 'a') as my_logger: 
        my_logger.write("训练{0}轮模型，需要时间约{1}分钟".format(str(train_round),str((end-start).seconds/60.0)))

