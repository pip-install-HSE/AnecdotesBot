import logging
import csv
import random

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import TG_TOKEN
from re import fullmatch


#
# class JokeStates(StatesGroup):
#     class MyState(State):
#         def set(self):
#             super(self).set()
#
#     WaitingForAnswer = MyState()


class ChatStates(StatesGroup):
    class MyState(State):
        def __init__(self, text=None):
            self.text = text
            super().__init__()

        async def set(self, message: types.Message = None):
            if self.text is not None and message is not None:
                await message.answer(self.text)
            await super().set()

    WaitingForAge = MyState('Hi, I can tell you a joke! How old are you? (Write the number)')
    RandomKind = MyState('Let’s pick a random kind of joke?', )
    GallowsHumor = MyState('And what about gallows humor?')
    RandomJoke = MyState()
    OneMoreJoke = MyState('Do you want one more similar joke or maybe something different?')
    # Test = State()


# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TG_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


def random_joke(data, similar=False):
    if 'answers_was' not in data:
        data['answers_was'] = []
    with open('qajokes1_1_2.csv', 'r', newline='') as csv_in:
        jokes = csv.DictReader(csv_in)
        jokes = [joke for joke in jokes if data['min'] <= float(joke['dirt']) <= data['max'] and joke['Answer'] not in data['answers_was']]

    if similar:
        similar_jokes = {}
        for joke in jokes:
            points = 0
            for kwid_word in data['kwid'].split('-'):
                if kwid_word in joke['kwid']:
                    points += 1
            if points not in similar_jokes:
                similar_jokes[points] = []
            similar_jokes[points].append(joke)
        # print(similar_jokes.keys())
        max_key = max(similar_jokes.keys())
        joke = random.choice(similar_jokes[max_key])
        # print(data['kwid'], joke['kwid'])
    else:
        joke = random.choice(jokes)
    # print(joke['Question'], joke['Answer'])
    data['answers_was'].append(joke['Answer'])
    data['question'] = joke['Question']
    data['answer'] = joke['Answer']
    data['kwid'] = joke['kwid']
    return data


@dp.message_handler(commands='start', state='*')
async def start(message: types.Message):
    await ChatStates.WaitingForAge.set(message)


@dp.message_handler(regexp=r'^[\s]*[0-9]+[\s]*$', state=ChatStates.WaitingForAge)
async def input_digits_in_state_age(message: types.Message, state: FSMContext):
    data = await state.get_data()
    age = int(message.text)
    if 1 <= age <= 99:
        data['age'] = age
        if age < 14:
            data['min'], data['max'] = 0.0, 0.0
            data = random_joke(data)
            await message.answer(data['question'])
            await ChatStates.RandomJoke.set(message)
        elif 14 <= age < 17:
            await ChatStates.GallowsHumor.set(message)
        elif age >= 18:
            await ChatStates.RandomKind.set(message)
    else:
        await message.answer('Please enter the age from 1 to 99.')
    await state.update_data(data)


@dp.message_handler(state=ChatStates.WaitingForAge)
async def input_not_digits_in_state_age(message: types.Message):
    await message.answer("Only digits, please.")


@dp.message_handler(state=ChatStates.RandomKind)
async def random_kind(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = fullmatch(r'\s*([\s\S]*)\s*', message.text).string
    if text == 'yes':
        data['min'], data['max'] = 0.0, 1.0
        data = random_joke(data)
        await message.answer(data['question'])
        await ChatStates.RandomJoke.set(message)
    elif text == 'no':
        await ChatStates.GallowsHumor.set(message)
    else:
        await message.answer('Please write yes or no.')
    await state.update_data(data)


@dp.message_handler(state=ChatStates.GallowsHumor)
async def gallows_humor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    age = data['age']
    text = fullmatch(r'\s*([\s\S]*)\s*', message.text).string
    if text == 'yes' or text == 'no':
        if 14 <= age <= 17:
            if text == 'yes':
                data['min'], data['max'] = 0.0, 0.5
            elif text == 'no':
                data['min'], data['max'] = 0.0, 0.25
        elif age >= 18:
            if text == 'yes':
                data['min'], data['max'] = 0.5, 1.0
            elif text == 'no':
                data['min'], data['max'] = 0.0, 0.5
        data = random_joke(data)
        await message.answer(data['question'])
        await ChatStates.RandomJoke.set(message)
    else:
        await message.answer("Please write yes or no.")
    await state.update_data(data)


@dp.message_handler(state=ChatStates.RandomJoke)
async def answer_for_random_joke(message: types.Message, state: FSMContext):
    data = await state.get_data()
    praises = [
        'You’re very talented! Look what i’ve got:',
        'Oh, that’s really cool! Hope you will also enjoy my answer:',
        'Ahahha, you rule! My variant was:',
        'Wow, that was great! I was thinking about this variant:',
        'What an imagination! My artificial intelligence generated this response:',
        'Well done! Hope my answer will make you laugh:',
        'Worthy of an Oscar! Let me share what I came up with:',
        'It’s a masterpiece! My thoughts was:',
        'High Five! My other variant was:'
    ]
    praise = random.choice(praises)
    await message.answer(f"{praise}\n{data['answer']}")
    await ChatStates.OneMoreJoke.set(message)


@dp.message_handler(lambda message: 'similar' in message.text, state=ChatStates.OneMoreJoke)
async def one_more_similar(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data = random_joke(data, similar=True)
    await state.update_data(data)
    await message.answer(data['question'])
    await ChatStates.RandomJoke.set(message)


@dp.message_handler(lambda message: 'different' in message.text, state=ChatStates.OneMoreJoke)
async def one_more_different(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data = random_joke(data)
    await state.update_data(data)
    await message.answer(data['question'])
    await ChatStates.RandomJoke.set(message)


@dp.message_handler(state=ChatStates.OneMoreJoke)
async def one_more_input_error(message: types.Message):
    await message.answer('similar or different?')


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer('Press /start to start')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
