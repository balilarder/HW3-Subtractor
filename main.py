from keras.models import Sequential
from keras import layers
import numpy as np
from six.moves import range
import csv

class colors:
    ok = '\033[92m'
    fail = '\033[91m'
    close = '\033[0m'

TRAINING_SIZE = 80000
# TRAINING_SIZE = 10

DIGITS = 3
REVERSE = False
MAXLEN = DIGITS + 1 + DIGITS

# MAXLEN = 6

chars = '0123456789+-* '
RNN = layers.LSTM
HIDDEN_SIZE = 128
BATCH_SIZE = 128
LAYERS = 1

class CharacterTable(object):
    def __init__(self, chars):
        self.chars = sorted(set(chars))
        self.char_indices = dict((c, i) for i, c in enumerate(self.chars))
        self.indices_char = dict((i, c) for i, c in enumerate(self.chars))
    
    def encode(self, C, num_rows):
        x = np.zeros((num_rows, len(self.chars)))
        
        for i, c in enumerate(C):
            x[i, self.char_indices[c]] = 1
        return x
    
    def decode(self, x, calc_argmax=True):
        if calc_argmax:
            x = x.argmax(axis=-1)
        return "".join(self.indices_char[i] for i in x)

ctable = CharacterTable(chars)

# Data Genaration
questions = []
expected = []
seen = set()
print('Generating data...')
while len(questions) < TRAINING_SIZE:
    f = lambda: int(''.join(np.random.choice(list('0123456789')) for i in range(np.random.randint(1, DIGITS + 1))))
    a, b = f(), f()
    if a < 100 or b < 100:
        continue
    # print(a)
    # print(b)
    key = tuple(sorted((a, b)))
    # print(key)
    if key in seen:
        continue
    seen.add(key)
    # q = '{}+{}'.format(a, b)
    r = np.random.randint(2)
    if r == 0:
        q = '{}+{}'.format(a, b)
    else:
        q = '{}-{}'.format(a, b)

    # q = '{}*{}'.format(a, b)

    # print(q, len(q))
    query = q + ' ' * (MAXLEN - len(q))
    # ans = str(a + b)
    if r == 0:
        ans = str(a + b)
    else:
        ans = str(a - b)

    # ans = str (a * b)
    ans += ' ' * (DIGITS + 1 - len(ans))
    if REVERSE:
        query = query[::-1]
    # print(query, len(query))
    # print(ans, len(ans))
    # print()
    questions.append(query)
    expected.append(ans)
print('Total addition questions:', len(questions))
print(questions[:5], expected[:5])

# Processing
print('Vectorization...')
x = np.zeros((len(questions), MAXLEN, len(chars)), dtype=np.bool)
y = np.zeros((len(expected), DIGITS + 1, len(chars)), dtype=np.bool)
# print(x[0])
# print(y[0])

for i, sentence in enumerate(questions):
    x[i] = ctable.encode(sentence, MAXLEN)
for i, sentence in enumerate(expected):
    y[i] = ctable.encode(sentence, DIGITS + 1)


indices = np.arange(len(y))
np.random.shuffle(indices)
# print(indices)
# print(x)
x = x[indices]
# print(x)
y = y[indices]

# train_test_split
train_x = x[:40000]
train_y = y[:40000]
test_x = x[40000:]
test_y = y[40000:]

split_at = len(train_x) - len(train_x) // 10
print(split_at)
(x_train, x_val) = train_x[:split_at], train_x[split_at:]
(y_train, y_val) = train_y[:split_at], train_y[split_at:]

print('Training Data:')
print(x_train.shape)
print(y_train.shape)

print('Validation Data:')
print(x_val.shape)
print(y_val.shape)

print('Testing Data:')
print(test_x.shape)
print(test_y.shape)

# print("input: ", x_train[:3], '\n\n', "label: ", y_train[:3])


# Build Model
print('Build model...')
model = Sequential()
model.add(RNN(HIDDEN_SIZE, input_shape=(MAXLEN, len(chars))))
model.add(layers.RepeatVector(DIGITS + 1))
for _ in range(LAYERS):
    model.add(RNN(HIDDEN_SIZE, return_sequences=True))

model.add(layers.TimeDistributed(layers.Dense(len(chars))))
model.add(layers.Activation('softmax'))
model.compile(loss='categorical_crossentropy',
              optimizer='adam',
              metrics=['accuracy'])
model.summary()


# Training
f = open("result.csv", 'w')
writer = csv.writer(f)


for iteration in range(100):
    print()
    print('-' * 50)
    print('Iteration', iteration)
    fitted_model = model.fit(x_train, y_train,
                             batch_size=BATCH_SIZE,
                             epochs=1,
                             validation_data=(x_val, y_val))

    loss_history = fitted_model.history
    print("logs")
    print(loss_history)


    for i in range(10):
        ind = np.random.randint(0, len(x_val))
        rowx, rowy = x_val[np.array([ind])], y_val[np.array([ind])]
        # print(rowx, rowy)
        preds = model.predict_classes(rowx, verbose=0)
        q = ctable.decode(rowx[0])
        correct = ctable.decode(rowy[0])
        guess = ctable.decode(preds[0], calc_argmax=False)
        print('Q', q[::-1] if REVERSE else q, end=' ')
        print('T', correct, end=' ')
        if correct == guess:
            print(colors.ok + '☑' + colors.close, end=' ')
        else:
            print(colors.fail + '☒' + colors.close, end=' ')
        print(guess)


    # Validation
    right = 0
    preds = model.predict_classes(test_x, verbose=0)
    for i in range(len(preds)):
        q = ctable.decode(test_x[i])
        correct = ctable.decode(test_y[i])
        guess = ctable.decode(preds[i], calc_argmax=False)
        # print('Q', q[::-1] if REVERSE else q, end=' ')
        # print('T', correct, end=' ')
        if correct == guess:
            # print(colors.ok + '☑' + colors.close, end=' ')
            right += 1
        # else:
            # print(colors.fail + '☒' + colors.close, end=' ')
        # print(guess)
    print("MSG : Accuracy is {}".format(right / len(preds)))
    writer.writerow([loss_history['loss'][0],
                    loss_history['acc'][0],
                    loss_history['val_loss'][0],
                    loss_history['val_acc'][0], 
                    right / len(preds)])
# Saving model
model.save('my_model.h5')