import unittest
import pytest
import pandas as pd

from analitico.schema import generate_schema, apply_schema

from .test_mixin import TestMixin

# pylint: disable=no-member


@pytest.mark.django_db
class DatasetTests(unittest.TestCase, TestMixin):
    """ Unit testing of Dataset functionality, reading, converting, transforms, saving, etc """

    ## Test creations

    def test_dataset_csv1_basics(self):
        """ Test empty dataset creation """
        try:
            ds = self.read_dataset_asset("ds_test_1.json")
            self.assertEqual(ds.id, "ds_1")

            df = ds.get_dataframe()
            self.assertTrue(isinstance(df, pd.DataFrame))
            self.assertEqual(len(df), 3)
            self.assertEqual(df.columns[0], "First")
            self.assertEqual(df.columns[1], "Second")
            self.assertEqual(df.columns[2], "Third")
            self.assertEqual(df.iloc[0, 0], 10)
            self.assertEqual(df.iloc[1, 1], 21)
            self.assertEqual(df.iloc[2, 2], 32)
        except Exception as exc:
            raise exc

    def test_dataset_csv2_types_default(self):
        """ Test standard data type conversions """
        try:
            ds = self.read_dataset_asset("ds_test_2.json")
            self.assertEqual(ds.id, "ds_2")

            df = ds.get_dataframe()
            self.assertEqual(df.dtypes[0], "int64")
            self.assertEqual(df.dtypes[1], "O")
            self.assertEqual(df.dtypes[2], "float64")
        except Exception as exc:
            raise exc

    def test_dataset_csv3_types_cast_float(self):
        """ Test forcing integers to be floating point instead """
        try:
            df = self.read_dataframe_asset("ds_test_3_cast_float.json")
            # would normally be int, but was forced to float
            self.assertEqual(df.dtypes[0], "float64")
            self.assertEqual(df.dtypes[1], "O")
            self.assertEqual(df.dtypes[2], "float64")
        except Exception as exc:
            raise exc

    def test_dataset_csv3_types_cast_string(self):
        """ Test forcing float column to string """
        try:
            df = self.read_dataframe_asset("ds_test_3_cast_string.json")
            self.assertEqual(df.dtypes[0], "int64")
            self.assertEqual(df.dtypes[1], "O")
            # third column would be float, but is cast to string
            self.assertEqual(df.dtypes[2], "O")
            self.assertEqual(df.iloc[2, 2], "32.50")
        except Exception as exc:
            raise exc

    def test_dataset_csv4_applyschema_rename(self):
        """ Test reading a table then renaming a column """
        try:
            df = self.read_dataframe_asset("ds_test_4.json")
            schema = generate_schema(df)

            columns = schema["columns"]
            self.assertEqual(len(columns), 3)
            self.assertEqual(df.columns[1], "Second")

            schema["columns"][1]["rename"] = "Secondo"
            df = apply_schema(df, schema)

            columns = df.columns
            self.assertEqual(df.columns[1], "Secondo")
        except Exception as exc:
            raise exc

    def test_dataset_csv4_applyschema_index(self):
        """ Test reading a table then making a column its index """
        try:
            df = self.read_dataframe_asset("ds_test_4.json")
            schema = generate_schema(df)

            columns = schema["columns"]
            self.assertEqual(len(columns), 3)
            self.assertEqual(df.index.name, None)

            schema["columns"][0]["index"] = True
            df = apply_schema(df, schema)

            columns = df.columns
            self.assertEqual(df.index.name, "First")
        except Exception as exc:
            raise exc

    def test_dataset_csv4_applyschema_index_rename(self):
        """ Test reading a table then making a column its index then renaming it """
        try:
            df = self.read_dataframe_asset("ds_test_4.json")
            schema = generate_schema(df)

            columns = schema["columns"]
            self.assertEqual(len(columns), 3)
            self.assertEqual(df.index.name, None)

            schema["columns"][0]["index"] = True
            schema["columns"][0]["rename"] = "Primo"
            df = apply_schema(df, schema)

            columns = df.columns
            self.assertEqual(df.index.name, "Primo")
            self.assertEqual(df.columns[0], "Primo")
        except Exception as exc:
            raise exc

    def test_dataset_csv4_types_datetime_iso8601(self):
        """ Test reading datetime in ISO8601 format """
        try:
            df = self.read_dataframe_asset("ds_test_4.json")
            self.assertEqual(df.dtypes[0], "int64")
            self.assertEqual(df.dtypes[1], "O")

            self.assertTrue(isinstance(df.iloc[0, 2], pd.Timestamp))
            self.assertTrue(isinstance(df.iloc[1, 2], pd.Timestamp))
            self.assertTrue(isinstance(df.iloc[2, 2], pd.Timestamp))
            self.assertTrue(isinstance(df.iloc[3, 2], pd.Timestamp))

            self.assertEqual(df.iloc[0, 2], pd.Timestamp("2019-01-20 00:00:00"))
            self.assertEqual(df.iloc[1, 2], pd.Timestamp("2019-01-20 16:30:15"))
            self.assertEqual(df.iloc[2, 2], pd.Timestamp("2019-02-01 00:00:00"))
            self.assertEqual(df.iloc[3, 2], pd.Timestamp("2019-01-01 00:00:00"))

            # Timezones are state machines from row to row...

            # 2019-09-15T15:53:00
            self.assertEqual(df.iloc[4, 2], pd.Timestamp("2019-09-15 15:53:00"))
            # 2019-09-15T15:53:00+05:00 (changes timezone)
            self.assertEqual(df.iloc[5, 2], pd.Timestamp("2019-09-15 10:53:00"))
            # 2019-09-15T15:53:00 (maintains +5 timezone)
            self.assertEqual(df.iloc[6, 2], pd.Timestamp("2019-09-15 10:53:00"))
            # 2019-09-15T15:53:00+00 (reverts timezone)
            self.assertEqual(df.iloc[7, 2], pd.Timestamp("2019-09-15 15:53:00"))
            # 2019-09-15T15:53:00-01:30 (changes timezone)
            self.assertEqual(df.iloc[8, 2], pd.Timestamp("2019-09-15 17:23:00"))
            # 20080915T155300Z (zulu time)
            self.assertEqual(df.iloc[9, 2], pd.Timestamp("2008-09-15 15:53:00"))

            # Time only uses today's date: 15:53:00.322348
            self.assertEqual(df.iloc[10, 2], pd.Timestamp("15:53:00.322348"))

            # Examples:
            # http://support.sas.com/documentation/cdl/en/lrdict/64316/HTML/default/viewer.htm#a003169814.htm
        except Exception as exc:
            raise exc

    def test_dataset_csv5_category_no_schema(self):
        """ Test reading categorical data without a schema """
        try:
            df = self.read_dataframe_asset("ds_test_5_category_no_schema.json")

            self.assertEqual(len(df.columns), 10)
            self.assertEqual(df.columns[0], "id")
            self.assertEqual(df.columns[1], "name")
            self.assertEqual(df.columns[2], "slug")
            self.assertEqual(df.columns[3], "parent_id")
            self.assertEqual(df.columns[4], "depth")
            self.assertEqual(df.columns[5], "priority")
            self.assertEqual(df.columns[6], "max_weight")
            self.assertEqual(df.columns[7], "frozen")
            self.assertEqual(df.columns[8], "rate")
            self.assertEqual(df.columns[9], "has_ingredients_book")

            # Column types
            self.assertEqual(df.dtypes[0], "int")  # id
            self.assertEqual(df.dtypes[1], "O")  # name
            self.assertEqual(df.dtypes[2], "O")  # slug
            self.assertEqual(df.dtypes[3], "float")  # parent_id
            self.assertEqual(df.dtypes[7], "int")  # frozen

            # Items types
            self.assertEqual(type(df.iloc[0, 1]).__name__, "str")  # name
            self.assertEqual(type(df.iloc[0, 2]).__name__, "str")  # slug
            self.assertEqual(type(df.iloc[0, 3]).__name__, "float64")  # parent_id
        except Exception as exc:
            raise exc

    def test_dataset_csv5_category_with_schema(self):
        """ Test reading categorical data with a schema, check types """
        try:
            df = self.read_dataframe_asset("ds_test_5_category_with_schema.json")

            self.assertEqual(len(df.columns), 10)
            self.assertEqual(df.columns[0], "id")
            self.assertEqual(df.columns[1], "name")
            self.assertEqual(df.columns[2], "slug")
            self.assertEqual(df.columns[3], "parent_id")
            self.assertEqual(df.columns[4], "depth")
            self.assertEqual(df.columns[5], "priority")
            self.assertEqual(df.columns[6], "max_weight")
            self.assertEqual(df.columns[7], "frozen")
            self.assertEqual(df.columns[8], "rate")
            self.assertEqual(df.columns[9], "has_ingredients_book")

            # Column types
            self.assertEqual(df.dtypes[0], "int")  # id
            self.assertEqual(df.dtypes[1], "category")  # name
            self.assertEqual(df.dtypes[2], "category")  # slug
            self.assertEqual(df.dtypes[3], "float")  # parent_id
            self.assertEqual(df.dtypes[7], "bool")  # frozen
        except Exception as exc:
            raise exc

    def test_dataset_csv5_category_check_values(self):
        """ Test reading categorical data, check values """
        try:
            df = self.read_dataframe_asset("ds_test_5_category_with_schema.json")

            # Items types
            self.assertEqual(type(df.iloc[0, 1]).__name__, "str")  # name
            self.assertEqual(type(df.iloc[0, 2]).__name__, "str")  # slug
            self.assertEqual(type(df.iloc[0, 3]).__name__, "float64")  # parent_id
            self.assertEqual(type(df.iloc[0, 7]).__name__, "bool_")  # frozen
        except Exception as exc:
            raise exc

    def test_dataset_csv5_category_no_index(self):
        """ Test reading categorical data, check index column """
        try:
            df1 = self.read_dataframe_asset("ds_test_5_category_with_schema.json")

            # By default the index column is the row number.
            # If the dataset has an index or id row it is just like
            # any other row and is not used to index the pandas dataset
            self.assertFalse(df1.loc[205, "frozen"])
            self.assertEqual(df1.loc[205, "slug"], "sughi-pronti-primi-piatti")
            self.assertEqual(df1.loc[205, "parent_id"], 100150)

            # Apply the correct index column manually
            df2 = df1.set_index("id", drop=False)
            self.assertFalse(df2.loc[205, "frozen"])
            self.assertEqual(df2.loc[205, "slug"], "carne-tacchino")
            self.assertEqual(df2.loc[205, "parent_id"], 100102)
        except Exception as exc:
            raise exc

    def test_dataset_csv5_category_with_index(self):
        """ Test reading categorical data, check explicit index column """
        try:
            df = self.read_dataframe_asset("ds_test_5_category_with_index.json")
            self.assertFalse(df.loc[205, "frozen"])
            self.assertEqual(df.loc[205, "slug"], "carne-tacchino")
            self.assertEqual(df.loc[205, "parent_id"], 100102)
        except Exception as exc:
            raise exc

    def test_dataset_csv6_weird_index_no_attr(self):
        """ Test reading table with 'weird' index column explicitly marked in schema """
        try:
            df = self.read_dataframe_asset("ds_test_6_weird_index_no_attr.json")
            self.assertEqual(df.loc[8, "slug"], "pasta-riso-cereali")
            self.assertEqual(df.loc[27, "slug"], "2-alt-pasta")
        except Exception as exc:
            raise exc

    def test_dataset_csv6_weird_index_with_attr(self):
        """ Test reading table with 'weird' index column explicitly marked in schema """
        try:
            df = self.read_dataframe_asset("ds_test_6_weird_index_with_attr.json")
            self.assertEqual(df.index.name, "indice")
            self.assertEqual(df.loc[8, "slug"], "pane-pasticceria")
            self.assertEqual(df.loc[27, "slug"], "sughi-scatolame-condimenti")
            self.assertEqual(df.loc[100598, "slug"], "2-alt-salumi")
        except Exception as exc:
            raise exc

    def test_dataset_csv7_timedelta(self):
        """ Test timespan to timedelta automatic conversion """
        try:
            df = self.read_dataframe_asset("ds_test_7_autoschema.json")

            # index is from column 'indice'
            self.assertEqual(df.loc[1, "elapsed"], pd.Timedelta("1 day"))
            self.assertEqual(df.loc[3, "elapsed"], pd.Timedelta("2 days"))
            self.assertEqual(df.loc[4, "elapsed"], pd.Timedelta("3 days"))
            self.assertEqual(df.loc[6, "elapsed"], pd.Timedelta("1 days 06:05:01.00003"))
        except Exception as exc:
            raise exc

    def test_dataset_csv7_autoschema(self):
        """ Test automatically generating an analitico schema from a pandas dataframe """
        try:
            df = self.read_dataframe_asset("ds_test_7_autoschema.json")
            schema = generate_schema(df)

            columns = schema["columns"]
            self.assertEqual(len(columns), 12)

            self.assertEqual(columns[0]["name"], "name")
            self.assertEqual(columns[0]["type"], "string")
            self.assertEqual(columns[1]["name"], "slug")
            self.assertEqual(columns[1]["type"], "category")
            self.assertEqual(columns[2]["name"], "parent_id")
            self.assertEqual(columns[2]["type"], "float")
            self.assertEqual(columns[3]["name"], "depth")
            self.assertEqual(columns[3]["type"], "integer")
            self.assertEqual(columns[4]["name"], "priority")
            self.assertEqual(columns[4]["type"], "integer")
            self.assertEqual(columns[5]["name"], "max_weight")
            self.assertEqual(columns[5]["type"], "integer")
            self.assertEqual(columns[6]["name"], "frozen")
            self.assertEqual(columns[6]["type"], "boolean")
            self.assertEqual(columns[7]["name"], "rate")
            self.assertEqual(columns[7]["type"], "float")
            self.assertEqual(columns[8]["name"], "has_ingredients_book")
            self.assertEqual(columns[8]["type"], "boolean")
            self.assertEqual(columns[9]["name"], "indice")
            self.assertEqual(columns[9]["type"], "integer")
            self.assertEqual(columns[9]["index"], True)
            self.assertEqual(columns[10]["name"], "updated_at")
            self.assertEqual(columns[10]["type"], "datetime")
            self.assertEqual(columns[11]["name"], "elapsed")
            self.assertEqual(columns[11]["type"], "timespan")
        except Exception as exc:
            raise exc

    def test_dataset_csv7_reordering(self):
        """ Test reordering of columns in the source """
        try:
            df = self.read_dataframe_asset("ds_test_7_reordering.json")
            self.assertEqual(len(df.columns), 12)
            self.assertEqual(df.columns[0], "depth")
            self.assertEqual(df.columns[1], "elapsed")
            self.assertEqual(df.columns[2], "frozen")
            self.assertEqual(df.columns[3], "has_ingredients_book")
            self.assertEqual(df.columns[4], "indice")
            self.assertEqual(df.columns[5], "max_weight")
            self.assertEqual(df.columns[6], "name")
            self.assertEqual(df.columns[7], "parent_id")
            self.assertEqual(df.columns[8], "priority")
            self.assertEqual(df.columns[9], "rate")
            self.assertEqual(df.columns[10], "slug")
            self.assertEqual(df.columns[11], "updated_at")
        except Exception as exc:
            raise exc

    def test_dataset_csv7_filtering(self):
        """ Test removing columns in the source """
        try:
            df = self.read_dataframe_asset("ds_test_7_filtering.json")
            self.assertEqual(len(df.columns), 4)
            self.assertEqual(df.columns[0], "indice")
            self.assertEqual(df.columns[1], "name")
            self.assertEqual(df.columns[2], "slug")
            self.assertEqual(df.columns[3], "frozen")
        except Exception as exc:
            raise exc

    def test_dataset_csv8_unicode(self):
        """ Test unicode chars in the source """
        try:
            df = self.read_dataframe_asset("ds_test_8_unicode.json")
            self.assertEqual(len(df.columns), 3)
            self.assertEqual(df.columns[0], "index")
            self.assertEqual(df.columns[1], "language")
            self.assertEqual(df.columns[2], "message")

            self.assertEqual(
                df.loc[0, "message"],
                "! \" # $ % & ' ( ) * + - . / 0 1 2 3 4 5 6 7 8 9 : ; < = > ? @ A B C D E F G H I J K L M N O P Q R S T U V W X Y Z [ \\ ] ^ _ ` a b c d e f g h i j k l m n o p q r s t u v w x y z { | } ~",
            )
            self.assertEqual(
                df.loc[1, "message"],
                "¡ ¢ £ ¤ ¥ ¦ § ¨ © ª « ¬ \xad ® ¯ ° ± ² ³ ´ µ ¶ · ¸ ¹ º » ¼ ½ ¾ ¿ À Á Â Ã Ä Å Æ Ç È É Ê Ë Ì Í Î Ï Ð Ñ Ò Ó Ô Õ Ö × Ø Ù Ú Û Ü Ý Þ ß à á â ã ä å æ ç è é ê ë ì í î ï ð ñ ò ó ô õ ö ÷ ø ù ú û ü ý þ ÿ",
            )
            self.assertEqual(
                df.loc[2, "message"],
                "Ё Ђ Ѓ Є Ѕ І Ї Ј Љ Њ Ћ Ќ Ў Џ А Б В Г Д Е Ж З И Й К Л М Н О П Р С Т У Ф Х Ц Ч Ш Щ Ъ Ы Ь Э Ю Я а б в г д е ж з и й к л м н о п р с т у ф х ц ч ш щ ъ ы ь э ю я ё ђ ѓ є ѕ і ї ј љ њ ћ ќ ў џ Ѡ ѡ Ѣ ѣ Ѥ ѥ Ѧ ѧ Ѩ ѩ Ѫ ѫ Ѭ ѭ Ѯ ѯ Ѱ ѱ Ѳ ѳ Ѵ ѵ Ѷ ѷ Ѹ ѹ Ѻ ѻ Ѽ ѽ Ѿ",
            )
            self.assertEqual(
                df.loc[3, "message"],
                "؛ ؟ ء آ أ ؤ إ ئ ا ب ة ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ـ ف ق ك ل م ن ه و ى ي ً ٌ ٍ َ ُ ِ ّ ْ ٠ ١ ٢ ٣ ٤ ٥ ٦ ٧ ٨ ٩ ٪ ٫ ٬ ٭ ٰ ٱ ٲ ٳ ٴ ٵ ٶ ٷ ٸ ٹ ٺ ٻ ټ ٽ پ ٿ ڀ ځ ڂ ڃ ڄ څ چ ڇ ڈ ډ ڊ ڋ ڌ ڍ ڎ ڏ ڐ ڑ ڒ ړ ڔ ڕ ږ ڗ ژ ڙ ښ ڛ ڜ ڝ ڞ ڟ ڠ ڡ ڢ ڣ ڤ ڥ ڦ ڧ ڨ ک",
            )
            self.assertEqual(
                df.loc[4, "message"],
                "ก ข ฃ ค ฅ ฆ ง จ ฉ ช ซ ฌ ญ ฎ ฏ ฐ ฑ ฒ ณ ด ต ถ ท ธ น บ ป ผ ฝ พ ฟ ภ ม ย ร ฤ ล ฦ ว ศ ษ ส ห ฬ อ ฮ ฯ ะ ั า ำ ิ ี ึ ื ุ ู ฺ ฿ เ แ โ ใ ไ ๅ ๆ ็ ่ ้ ๊ ๋ ์ ํ ๎ ๏ ๐ ๑ ๒ ๓ ๔ ๕ ๖ ๗ ๘ ๙ ๚ ๛",
            )
            self.assertEqual(
                df.loc[5, "message"],
                "一 丁 丂 七 丄 丅 丆 万 丈 三 上 下 丌 不 与 丏 丐 丑 丒 专 且 丕 世 丗 丘 丙 业 丛 东 丝 丞 丟 丠 両 丢 丣 两 严 並 丧 丨 丩 个 丫 丬 中 丮 丯 丰 丱 串 丳 临 丵 丶 丷 丸 丹 为 主 丼 丽 举 丿 乀 乁 乂 乃 乄 久 乆 乇 么 义 乊 之 乌 乍 乎 乏 乐 乑 乒 乓 乔 乕 乖 乗 乘 乙 乚 乛 乜 九 乞 也 习 乡 乢 乣 乤 乥 书 乧 乨 乩 乪 乫 乬 乭 乮 乯 买 乱 乲 乳 乴 乵 乶 乷 乸 乹 乺 乻 乼 乽 乾 乿",
            )
        except Exception as exc:
            raise exc

    def test_dataset_csv9_types_datetime_nulls(self):
        """ Test reading datetime that has null values """
        try:
            df = self.read_dataframe_asset("ds_test_9.json")
            self.assertEqual(df.dtypes[0], "int64")
            self.assertEqual(df.dtypes[1], "O")
            self.assertTrue(df.dtypes[2] == "datetime64[ns]")

            self.assertTrue(isinstance(df.iloc[0, 2], pd.Timestamp))
            self.assertTrue(isinstance(df.iloc[1, 2], pd.Timestamp))

            # all these are variantions on None and null
            self.assertTrue(pd.isnull(df.iloc[2, 2]))
            self.assertTrue(pd.isnull(df.iloc[3, 2]))
            self.assertTrue(pd.isnull(df.iloc[4, 2]))
            self.assertTrue(pd.isnull(df.iloc[5, 2]))
            self.assertTrue(pd.isnull(df.iloc[6, 2]))
        except Exception as exc:
            raise exc

    # TODO: test reading number that use . for thousands (eg: en-us, locale)

    # TODO: test datetime in localized formats

    # TODO: test missing values in various formats

    # TODO: test replacing missing values

    # TODO: test plugins pipeline

    # TODO: test modified values after plugin pipeline

    # TODO: test modified schema after plugin pipeline
