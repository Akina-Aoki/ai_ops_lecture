# Podcast script: "LanceDB, explained by your teacher" (lecture 09)

**Format:** one teacher talking to one student (you), about 25 minutes when read aloud at a relaxed pace.
**Who it is for:** a junior data engineer who has never worked with embeddings or vectors.
**How to use it:** read it like a story, or paste it into a text-to-speech tool to listen to it. There are no code blocks and no tables on purpose: everything is written to be *heard*. Where the teacher says "pause", stop for a few seconds and try to answer the question in your head before continuing.
**Keep open next to it (optional):** [lancedb_basics.ipynb](lancedb_basics.ipynb), [lancedb_embeddings.ipynb](lancedb_embeddings.ipynb), [custom_embeddings/nvidia_nemotron.py](custom_embeddings/nvidia_nemotron.py), and [STUDY_GUIDE.md](STUDY_GUIDE.md).

| Chapter | Topic | About |
| --- | --- | --- |
| 0 | Welcome and the map | 1 min |
| 1 | The problem: why a normal database is not enough | 2 min |
| 2 | What an embedding really is | 3 min |
| 3 | LanceDB: a database that is just a folder | 2 min |
| 4 | The animals demo: vector search with three numbers | 3 min |
| 5 | Letting LanceDB create the embeddings for you | 3 min |
| 6 | Three kinds of search, and hybrid | 3 min |
| 7 | The custom NVIDIA embedder | 4 min |
| 8 | Traps that will bite you | 2 min |
| 9 | Recap and homework | 1 min |

---

## Chapter 0. Welcome and the map

Hello, and welcome. Today is lecture nine, and it is the day we start building the foundation for something called RAG. You have seen agents, tools, FastAPI, and Logfire. Today there is no agent at all. No PydanticAI, no web server. Just notebooks, two small data files, and one short Python file. And that is on purpose, because today we learn how to store text in a way that a computer can search by meaning.

Let me give you the map first, so you never feel lost. We have two notebooks. The first one, lancedb basics, teaches how LanceDB works, from connecting to a database all the way to something called hybrid search. The second one, lancedb embeddings, shows how to change the model that turns text into numbers, and how to write your own. Then we have one Python file, nvidia nemotron, inside a folder called custom embeddings. And two data files: a tiny one about animals, and one with thirty jokes.

If at any moment you feel confused, come back to this one sentence. Today's whole lecture is this: text goes in, an embedding model turns it into numbers, LanceDB stores both, and later we search by meaning. Text, numbers, store, search. Ready? Let's go.

---

## Chapter 1. The problem

Imagine you work at a company, and you have ten thousand support documents. A colleague asks your chatbot: "How do I get my money back?" And the right document is titled "Refund policy". Notice something? The question does not contain the word "refund". And the document does not contain the words "money back".

Now think about the tools you know. In SQL you would write a where clause. Where title equals something, or where text like percent refund percent. Those tools match **words**. They look for the same characters. They do not understand that "money back" and "refund" mean the same thing.

So here is the problem for today. We want to search by **meaning**, not by spelling. And the answer to that problem is: embeddings.

Pause for a second. Think about a real example from your own work where the words in the question and the words in the data would not match, but the meaning would. Got one? Good. Keep it in mind. That is exactly the kind of problem we solve today.

---

## Chapter 2. What an embedding really is

Here is the most important idea of the whole lecture, so I will go slowly.

An embedding is a list of numbers that represents the meaning of a text.

Think about GPS. Every place on Earth has coordinates: two numbers. And places that are close to each other have close coordinates. You can tell that two cities are near each other just by comparing their coordinates, without seeing a map.

An embedding does the same thing, but for meaning. There is a model, called an embedding model, and you give it a text. It gives you back a list of numbers. And the rule is this: texts that mean similar things get similar numbers. Texts that mean different things get different numbers.

Let me give you a tiny example. Pretend the model only uses three numbers. For the word "cat" it gives point nine, point eight, point one. For "kitten" it gives point eight five, point seven five, point one five. And for "invoice" it gives point one, point two, point nine five.

Look at the first two. They are almost the same. Cat and kitten are close. And invoice looks completely different. To measure this, we use something called distance. You take each number, subtract, square it, and add up. Between cat and kitten you get zero point zero zero seven five. Very small, so very close. Between cat and invoice you get about one point seven. Big, so far apart. Smaller distance means more similar. Write that down: **smaller distance, more similar.**

Now, three important warnings, because this is where beginners get confused.

First: you never read these numbers. Number seventeen out of four thousand does not mean "is it an animal". A single number means nothing. Only the distance between two lists means something.

Second: an embedding is not a hash. A hash is designed so that cat and kitten come out completely different. An embedding is the opposite. Similar meaning, similar numbers.

Third: you can only compare numbers that came from the **same model**. Every model has its own number language. Comparing numbers from two different models is like comparing kilometres with Fahrenheit.

As a data engineer, here is how I want you to think about it. A normal column lets you join on equality. An embedding column lets you join on **closeness**. Same table, same ideas, but instead of where text equals something, you say: order by distance, limit ten. Give me the ten closest.

Pause. Can you say, in your own words, what an embedding is, in one sentence? Try it. "A list of numbers where similar meaning gives similar numbers." That is it.

---

## Chapter 3. LanceDB: a database that is just a folder

So where do we store these lists of numbers? In a vector database. Ours is called LanceDB.

Here is the nice thing for you as a data engineer. LanceDB is like DuckDB. It is embedded. That means there is no server to install, no port, no password. When you write lancedb dot connect and give it a name like vector database, LanceDB simply creates a **folder** with that name. That folder is your database. If you copy the folder, you copied the database.

Inside, each table is its own folder that ends with dot lance. And inside that folder there are three things: a folder with the data, a folder with versions, and a folder with transactions. If you have used Delta Lake or Iceberg, this will feel familiar. Data files plus a log. That is why, when you add rows to a table, the notebook prints "version two". Every change creates a new version of the table.

A table here looks like a normal table. It has columns with types. In our examples, one column holds the text, and another column holds the vector, the list of numbers. That is all.

Two small tips from the notebook. When you create a table you can say exist ok equals true, which means "if the table is already there, just open it, do not crash". That is the same as create table if not exists. Or you can say mode equals overwrite, which means "replace it if it exists", the same as create or replace. Be careful with overwrite, it deletes the old data.

---

## Chapter 4. The animals demo

Now the first demo, and I love this one because you can do it with a pencil.

The animals file has six animals. A dog running, a cat on a sofa, an elephant drinking, a cheetah sprinting, a parrot on a branch, a frog on a lily pad. And next to each sentence there are three numbers, which I made up by hand. So no AI model is used here at all. We are only learning how searching with numbers works.

We create a table from this data. LanceDB looks at the data and guesses the columns: text is a string, vector is a list of three decimal numbers. Then we add two more animals, a panda and a lion. The notebook prints version two. Good.

Now the search. We give LanceDB a list of three numbers: point five, point two, point nine. And we say: give me the three closest rows. LanceDB compares our numbers with the numbers of every row, and returns the panda, the cheetah, and the elephant. And next to each row there is a column called underscore distance. For the panda it is zero point zero three five four. That is very small, so the panda is the closest.

You can verify this by hand. Panda is point five one, point three seven, point eight two. The differences from our query are point zero one, point one seven, and minus point zero eight. Square them: point zero zero zero one, point zero two eight nine, point zero zero six four. Add them up: point zero three five four. Exactly what LanceDB says. One detail: LanceDB does not take the square root. It reports the squared distance. Still, smaller means closer.

And here is one more important thing the demo shows. Vector search **always** returns something. We asked for three rows, we got three rows. It never says "no match". It simply returns the nearest ones, even if the nearest are not really close. Remember that when we build real applications.

---

## Chapter 5. Letting LanceDB create the embeddings

In the animals demo, I typed the numbers by hand. In real life, nobody does that. We want to give LanceDB only the text, and let a model create the numbers.

LanceDB has something called the embeddings registry. Think of it as a catalogue of embedding providers. You say get registry dot get, and a name, like cohere, and then create, with the name of the model. Now you have an embedding model object.

Then comes the clever part. You describe your table with a class. It is a LanceModel, and if you remember lecture three, that is a Pydantic model. The class has two fields. The first is the text, and you mark it with source field. That means: this is the **input**, send this text to the embedding model. The second is the vector, marked with vector field. That means: this is the **output**, put the numbers here. And the size of the vector comes from the model, by asking it how many dimensions it has.

After that, you just call table dot add with your data, and you only provide the text column. LanceDB sends each text to the model, gets the numbers back, and stores them in the vector column for you. In the notebook we load thirty jokes with pandas, add them, and then the vector column is there, filled with numbers.

As a data engineer, think of it as a computed column. You declare, once, "this column is derived from that column using this function". Then every insert is enriched automatically.

Now we search with plain text. Search "give me chemistry related jokes". LanceDB turns **your question** into numbers using the same model, then finds the nearest jokes. And you will see the chemistry jokes come first. Search "data engineering jokes" and you get the data lake joke and the pipeline joke. The words do not have to match. The meaning matches.

Now an important rule that comes out of this. You must use the **same model** to store and to search. And the vector length must match the table. A table built for one size of vector cannot accept another size.

A word about Cohere, since the notebook uses it. It is a paid hosted API, and you need an API key in your environment. If you forget the key, the error appears when you add rows, not when you create the model. That surprises many beginners. And one more thing: in your installed version, the vector length of this Cohere model may not be the same as what the old saved output shows. Always check by asking the model for its number of dimensions.

---

## Chapter 6. Three kinds of search

Let's talk about search types, because this is a favourite interview question.

The first kind is vector search. It matches by meaning. It is great for "jokes about nature". But it is weak with exact things, like a product code or a name, and, as we said, it always returns something.

The second is full text search, or FTS. That is the classic keyword search. LanceDB builds an index of words, like the index at the back of a book. You create it with create fts index on the text column. It is perfect for exact words, like "C sharp". But it misses synonyms. It will not know that "car" and "automobile" are related.

The third is hybrid search, and it combines both. You ask for query type hybrid, and LanceDB runs the vector search and the keyword search, and gets two ranked lists. Then it needs to merge them into one. That is the job of a reranker, and the one we use is called RRF, reciprocal rank fusion.

Here is how RRF works, simply. Each row gets a score from its **position** in each list. First place gets a bigger score than fifth place. If a row appears in both lists, the scores are added. So a row that is good in both lists beats a row that is excellent in only one. Imagine a row that is first in the meaning list and third in the keyword list. It will beat a row that is second in one list and absent in the other. The nice thing: RRF does not need to compare the different score scales. It only uses positions.

The rule of thumb from the notebook is easy to remember. Exact matching, use full text search. Meaning-based matching, use vector search. Unpredictable or mixed questions, use hybrid. And if you are not sure, hybrid is a safe choice.

Pause. A user types a product code, like "A B dash four seven one one". Which search do you use? Full text. Exact string. Good.

---

## Chapter 7. The custom NVIDIA embedder

Now the part that I know is the hardest. Take a breath. We are going to go slowly, and I promise it is simpler than it looks.

Second notebook. First we use a free model that runs on your own computer, from a library called sentence transformers. It downloads from Hugging Face the first time, then it works offline, with no key and no cost. It is small, it supports many languages, and you can even search in another language, for example the word "kemi", and it still finds the English chemistry jokes. That is because the model is multilingual.

But then the lecturer wanted to use an NVIDIA model, and LanceDB does not have a built-in connector for it. So we write our own. That is the file nvidia nemotron dot py.

First, what is this file **not**? It is **not** the embedding model. The model runs on NVIDIA's servers. This file is a small wrapper that calls them. Think of it as the **transform step** of an ETL job. Extract is reading the jokes. Load is LanceDB storing them. And this file is the transform: it takes a text and returns the numbers.

Let me walk through the file in the order it runs.

At the top, it reads your environment file, to get your NVIDIA key. Then it creates one client, using the OpenAI Python library. Why OpenAI? Because NVIDIA's API copies the OpenAI format, so we reuse that client and only change the address. Same trick as in the earlier lectures. This client has retries and a time limit. And notice: this is created once at the top, and reused, like a database connection.

Then comes a line with an at sign. That is a decorator, and it registers our class in LanceDB's catalogue, under the name nvidia dash nemotron. This is how the notebook can later ask the catalogue for that name. And this explains a small mystery: the notebook imports the class but never uses it by name. The import itself is what runs the decorator. Without the import, the catalogue does not know the name.

Then the class. It extends a LanceDB class called text embedding function. That means: LanceDB already knows how to work with text embedders, and we only fill in the NVIDIA part. In programming language, we implement an interface. If you have written an Airflow operator or a dbt adapter, it is the same pattern. The framework defines the shape, you implement it for a new system.

The class has two settings: the model name, and the dimensions, which is four thousand ninety six. That is how many numbers each vector has. Careful: **we** declare this number. The code does not check it. If it differs from what NVIDIA really returns, the table will refuse the data.

Then the methods. One tells LanceDB the vector length. One, called embed one, is the only method that touches the network. It sends one text to NVIDIA and gets back a list of numbers, which we convert to a numpy array of float thirty two, because that is what LanceDB stores. Another one loops over a list of texts. And then the two that LanceDB actually calls.

When you add rows, LanceDB calls compute source embeddings. When you search, it calls compute query embeddings. Both end up in embed one, but with a different label: passage or query.

Why the two labels? Because a question and its answer do not look alike. "What is the capital of France?" and "Paris is a city on the river Seine" share few words. NVIDIA's model is trained to place a question near its matching documents, but it needs to know which side it is looking at. When I tested it, I embedded the word hello both ways, and the two lists of numbers were not identical. So the label really changes the result. Rule: store as passage, search as query.

And a number to remember for later: each vector is four thousand ninety six numbers, four bytes each, so about sixteen kilobytes per row. For thirty jokes, nothing. For a million rows, around sixteen gigabytes. Bigger vectors give more detail but cost more storage and more time. A real trade-off for a data engineer.

Also remember: one API call per joke. Thirty jokes, thirty calls. For thousands of rows you would batch them.

Pause. If someone asks you "what does this file do?", what do you say? "It teaches LanceDB how to turn text into vectors using the NVIDIA API, and registers itself under a name." Say it out loud once.

---

## Chapter 8. Traps that will bite you

Let me finish the content with the traps, because I want you to avoid losing an afternoon.

One. The schema decides which model is used. In the second notebook, the NVIDIA table was first built with the schema of the **local** model, so NVIDIA was never called. Creating an embedding object does nothing until a schema uses it. Now it has its own schema class. Lesson: always check the vector length of the column. If you expect four thousand ninety six and see three eighty four, the wrong model ran.

Two. Column names must match. In one notebook the text column is called joke, in the other jokes. If the data frame column and the schema field do not match, it will not work.

Three. Re-running cells. Creating a table twice without exist ok fails. And adding the same data twice gives you duplicates. Know what your cell does when you run it again. A real example from this very notebook: an old table called jokes already existed with different columns, and the demo cell failed with "schema does not match".

Four. Windows and encoding. Opening the jokes file without saying utf eight fails on Windows, because of the curly quotes.

Five. API keys. Cohere needs one name, NVIDIA another, and the Gemini embedder in LanceDB looks for a variable called google api key, even if your key is a Gemini key. Keys are read when you call, and a restart of the kernel may be needed after you change the environment file.

Six. Vector search never says "no match". In a real app, look at the distance and decide a cut-off.

---

## Chapter 9. Recap and homework

Let's recap in five sentences.

One. An embedding turns text into a list of numbers, so similar meaning gives similar numbers.

Two. LanceDB stores text and numbers together, in a folder, with no server.

Three. You search by turning the question into numbers and returning the rows with the smallest distance.

Four. Use full text search for exact words, vector search for meaning, hybrid for both, merged by RRF.

Five. A custom embedder is only an adapter: a class with a name in the catalogue that knows how to call a model and return numbers.

Now, homework. Three small exercises.

First: open the second notebook and run a small cell that creates the NVIDIA embedder and embeds the word hello. Print the length. You should see four thousand ninety six.

Second: do the distance calculation of the animals demo by hand for the frog. If you get point five eight four one, you understood it.

Third: write, in your own words, in three sentences, what the nvidia nemotron file does and what it does **not** do. Then compare with section four point three in the study guide.

And write your questions in the last section of the study guide, called "My questions". Next time, we will use all of this to build the real thing: a chatbot that finds the right documents first, and then answers. Thank you for listening, and see you in the next lecture.

---

## Teacher's cheat sheet (for after the podcast)

| Say this | Meaning |
| --- | --- |
| Embedding | A list of numbers for the meaning of a text |
| Distance | How far apart two lists are. Smaller means more similar |
| Source field / vector field | The input column, and the column where the numbers are stored |
| Registry | LanceDB's catalogue of embedding providers |
| FTS | Keyword search with a word index |
| Hybrid | Vector plus FTS, merged by a reranker |
| RRF | Score by rank in each list, then add |
| Passage / query | The two labels NVIDIA wants: stored document, or search question |
| Decorator | The at-sign line that registers the class |
