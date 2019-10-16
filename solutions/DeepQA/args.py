class args:
    def __init__(self):
        # data args
        self.line_path = "data/jddc/chat_100.txt"
        #self.line_path = "data/cornell/movie_lines.txt"
        #self.conv_path = "data/cornell/movie_conversations.txt"
        self.train_samples_path = "data/jddc/train_samples.pkl"
        self.sr_word_id_path = "data/jddc/word_id.pkl"
        self.vacab_filter = 1
        self.corpus_name = "jddc"

        # model args
        self.maxLengthEnco = 16
        self.maxLengthDeco = 16
        self.maxLength = 16
        self.embedding_size = 64
        self.hidden_size = 32
        self.rnn_layers = 2
        self.dropout = 0.9
        self.batch_size = 48
        self.learning_rate = 0.002
        self.beta1 = 0.9
        self.beta2 = 0.999
        self.epsilon = 1e-08
        self.softmaxSamples = 0

        # train args
        self.log_device_placement = False
        self.allow_soft_placement = True
        self.num_checkpoints = 100
        self.epoch_nums = 3
        self.checkpoint_every = 100
        self.evaluate_every = 100
        self.test = None
        # self.test = 'interactive'
        # self.test = 'web_interface'