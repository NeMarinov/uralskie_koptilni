import asyncio
import logging
from functools import lru_cache

from aiogram import Bot, Dispatcher
from aiogram.methods import DeleteWebhook
from aiogram import types, F
from aiogram.types import InlineKeyboardButton, FSInputFile, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import os

import config
import parser

load_dotenv()

print("TOKEN:", os.getenv("BOT_TOKEN"))
logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

user_selections = {}

@lru_cache(maxsize=1)
def get_products_list():
    return tuple(parser.first_find_function_kopt(i) for i in range(parser.get_count()))

@lru_cache(maxsize=50)
def get_product_detail(product_id):
    return parser.second_find_function_kopt(product_id)

@lru_cache(maxsize=10)
def get_product_additionally(index):
    return parser.third_find_function_additionally(index)


class KeyboardBuilder:
    def __init__(self):
        self.builder = InlineKeyboardBuilder()

    def add_row(self, *buttons):
        self.builder.row(*[
            InlineKeyboardButton(text=text, callback_data=callback)
            for text, callback in buttons
        ])
        return self

    def add_back(self, callback="back"):
        self.builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=callback))
        return self

    def build(self):
        return self.builder.as_markup()


class KeyboardFactory:
    @staticmethod
    def main_menu():
        return (KeyboardBuilder()
                .add_row((config.button1_text, "catalog"), (config.button2_text, "question"))
                .add_row((config.button3_text, "cost"))
                .build())

    @staticmethod
    def catalog_menu():
        builder = KeyboardBuilder()
        row = []
        for i, product in enumerate(get_products_list()):
            row.append((product['name'], f"kopt_{i}"))
            if len(row) == 2:
                builder.add_row(*row)
                row = []
        if row:
            builder.add_row(*row)
        return builder.add_back("back_to_main_menu").build()

    @staticmethod
    def info_product():
        return KeyboardBuilder().add_back("back_to_catalog_menu").build()

    @staticmethod
    def cost_of_product(product_id, selected_options=None):
        if selected_options is None:
            selected_options = set()

        builder = KeyboardBuilder()
        product = get_product_additionally(product_id)

        i = 1
        row = []
        while f'name_{i}' in product:
            checkbox = "✅" if i in selected_options else "☐"
            button_text = f"{checkbox} {product[f'name_{i}']}"
            row.append((button_text, f"toggle_option_{product_id}_{i}"))
            if len(row) == 2:
                builder.add_row(*row)
                row = []
            i += 1

        if row:
            builder.add_row(*row)

        builder.add_row(("💰 Рассчитать стоимость", f"calculate_{product_id}"))
        builder.add_back("back_to_cost_menu")
        return builder.build()

    @staticmethod
    def cost_menu():
        builder = KeyboardBuilder()
        row = []
        for i, product in enumerate(get_products_list()):
            row.append((product['name'], f"cost_kopt_{i}"))
            if len(row) == 2:
                builder.add_row(*row)
                row = []
        if row:
            builder.add_row(*row)
        return builder.add_back("back_to_main_menu").build()


class BACK:
    @staticmethod
    async def back_to_catalog_menu(callback: types.CallbackQuery):
        await callback.answer()
        await callback.message.edit_text(
            text="📦 <b>Каталог коптилен</b>\n\nВыберите интересующую модель:",
            parse_mode='HTML',
            reply_markup=KeyboardFactory.catalog_menu()
        )

    @staticmethod
    async def back_to_main_menu(callback: types.CallbackQuery):
        await callback.answer()
        await callback.message.delete()
        await bot.send_photo(
            callback.message.chat.id,
            photo=config.picture1,
            reply_markup=KeyboardFactory.main_menu()
        )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = f"<b>Приветствуем</b>, <u>{message.from_user.first_name}</u>! Вы в 'Уральских коптильнях'. Я помогу быстро прицениться и выбрать модель под ваши задачи. Что вас интересует?"
    msg = await message.answer(text, parse_mode='HTML')
    await asyncio.sleep(3)
    await msg.delete()
    await bot.send_photo(
        message.chat.id,
        photo=config.picture1,
        caption="Вот что я могу",
        reply_markup=KeyboardFactory.main_menu()
    )


@dp.callback_query(F.data == "catalog")
async def cmd_catalog(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        text="📦 <b>Каталог коптилен</b>\n\nВыберите интересующую модель:",
        parse_mode='HTML',
        reply_markup=KeyboardFactory.catalog_menu()
    )


@dp.callback_query(F.data == "cost")
async def cmd_cost(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        text="💸 <b>Рассчет стоимости с допами</b>\n\nЗдесь Вы можете рассчитать стоимость коптильни с дополнительным оборудованием:",
        parse_mode='HTML',
        reply_markup=KeyboardFactory.cost_menu()
    )


@dp.callback_query(F.data.startswith("kopt_"))
async def cmd_kopt(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.delete()

    product_id = int(callback.data.split("_")[1])
    product = get_product_detail(product_id)

    text = "<b>Комплектация:</b>\n\n"
    i = 1
    while f'name_{i}' in product:
        text += f"• {product[f'name_{i}']}\n"
        text += f"  Количество: {product[f'count_{i}']}\n\n"
        i += 1

    await callback.message.answer(text, parse_mode='HTML', reply_markup=KeyboardFactory.info_product())


@dp.callback_query(F.data.startswith("cost_kopt_"))
async def cmd_cost_kopt(callback: CallbackQuery):
    await callback.answer()

    product_id = int(callback.data.split("_")[2])
    product = get_product_additionally(product_id)
    base_product = get_products_list()[product_id]

    user_id = callback.from_user.id
    if user_id not in user_selections:
        user_selections[user_id] = {}
    user_selections[user_id][product_id] = set()

    text = f"<b>{base_product['name']}</b>\n\n"
    text += f"💰 Базовая цена: {base_product['price']}\n\n"
    text += "<b>Выберите дополнительные опции:</b>\n\n"

    i = 1
    while f'name_{i}' in product:
        text += f"• {product[f'name_{i}']} - {product[f'price_{i}']}\n"
        i += 1

    await callback.message.edit_text(
        text=text,
        parse_mode='HTML',
        reply_markup=KeyboardFactory.cost_of_product(product_id, frozenset(user_selections[user_id][product_id]))
    )


@dp.callback_query(F.data.startswith("toggle_option_"))
async def toggle_option(callback: CallbackQuery):
    await callback.answer()

    parts = callback.data.split("_")
    product_id = int(parts[2])
    option_id = int(parts[3])

    user_id = callback.from_user.id

    if option_id in user_selections[user_id][product_id]:
        user_selections[user_id][product_id].remove(option_id)
    else:
        user_selections[user_id][product_id].add(option_id)

    product = get_product_additionally(product_id)
    base_product = get_products_list()[product_id]

    text = f"<b>{base_product['name']}</b>\n\n"
    text += f"💰 Базовая цена: {base_product['price']}\n\n"
    text += "<b>Выберите дополнительные опции:</b>\n\n"

    i = 1
    while f'name_{i}' in product:
        text += f"• {product[f'name_{i}']} - {product[f'price_{i}']}\n"
        i += 1

    await callback.message.edit_text(
        text=text,
        parse_mode='HTML',
        reply_markup=KeyboardFactory.cost_of_product(product_id, frozenset(user_selections[user_id][product_id]))
    )


@dp.callback_query(F.data.startswith("calculate_"))
async def calculate_cost(callback: CallbackQuery):
    await callback.answer()

    product_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    selected = user_selections[user_id][product_id]
    base_product = get_products_list()[product_id]
    product = get_product_additionally(product_id)

    base_price = int(base_product['price'].replace('₽', '').replace('\u00a0', '').replace(' ', '').strip())
    total = base_price

    text = f"<b>Расчет стоимости: {base_product['name']}</b>\n\n"
    text += f"Базовая цена: {base_price:,}₽\n\n"
    text += "<b>Выбранные опции:</b>\n"

    if not selected:
        text += "Нет выбранных опций\n"
    else:
        for option_id in sorted(selected):
            option_name = product[f'name_{option_id}']
            option_price_str = product[f'price_{option_id}']
            option_price = int(option_price_str.replace('₽', '').replace('\u00a0', '').replace(' ', '').strip())
            total += option_price
            text += f"• {option_name}: +{option_price:,}₽\n"

    text += f"\n<b>Итого: {total:,}₽</b>"

    builder = KeyboardBuilder()
    builder.add_row(("🔙 Изменить выбор", f"cost_kopt_{product_id}"))
    builder.add_back("back_to_cost_menu")

    await callback.message.edit_text(
        text=text,
        parse_mode='HTML',
        reply_markup=builder.build()
    )


# ИСПРАВЛЕНО: было cost_of_product() без аргументов — падало с TypeError
@dp.callback_query(F.data == "back_to_cost_menu")
async def back_to_cost_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        text="💸 <b>Рассчет стоимости с допами</b>\n\nЗдесь Вы можете рассчитать стоимость коптильни с дополнительным оборудованием:",
        parse_mode='HTML',
        reply_markup=KeyboardFactory.cost_menu()  # ← было cost_of_product(), теперь cost_menu()
    )


@dp.callback_query(F.data == "back_to_catalog_menu")
async def back_to_catalog(callback: types.CallbackQuery):
    await BACK.back_to_catalog_menu(callback)


@dp.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    await BACK.back_to_main_menu(callback)


async def main():
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
