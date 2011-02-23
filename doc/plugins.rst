Come scrivere un plugin per pinolo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Introduzione
============
Il sistema di plugin e' attualmente gestito con la libreria Yapsy_ (almeno
finche' qualcuno non scrivera' o proporra' un sistema migliore); la
documentazione (orrenda) di base per la scrittura di un plugin Yapsy_ la si puo'
trovare `qui <http://yapsy.sourceforge.net/PluginManager.html>`_ e `qui
<http://yapsy.sourceforge.net/IPlugin.html>`_, ma come al solito la soluzione
migliore e' *Use the source, Luke!* guardando i sorgenti dei plugin di pinolo
gia' esistenti.


Descrizione di un tipico plugin
===============================
Verra' ora descritto uno dei plugin inclusi in pinolo: il plugin **prcd**.

Ogni plugin deve eseguire i seguenti *import*::

    from pinolo.main import CommandPlugin, PluginActivationError
    from pinolo import MyOptionParser, OptionParserError

La classe del plugin invece deve derivare da ``CommandPlugin`` e se vuole
utilizzare ``getopt`` deve creare un attributo di istanza per ogni *comando* da
gestire; la sintassi per ``MyOptionParser`` e' identica a quella di
``OptionParser`` incluso nel Pitone standard.

::

    class Prcd(CommandPlugin):
        """This is the PRCD plugin"""

        prcd_opt = MyOptionParser(usage="!prcd [options]")
        cowsay_opt = MyOptionParser(usage="!PRCD [options]")

L'inizializzazione del plugin puo' essere gestita nel metodo ``__init__`` della
classe, ma se il plugin necessita di una configurazione esterna (ad esempio
attraverso il file di configurazione principale) si dovra' usare il metodo
``activate`` che riceve come parametro opzionale ``config``.

L'oggetto ``config`` attualmente e' una ``namedtuple`` i cui attributi
contengono la configurazione; ad esempio::

    >>> config.quotes_db
    "/path/to/quotes.sqlite3"

Un esempio di ``activate`` che utilizza il parametro ``config`` per
inizializzare il plugin::

    def activate(self, config):
        super(QuotesDb, self).activate()

        self.db_file = 'sqlite:///' + config.quotes_db

Un plugin interagisce con gli eventi esterni attraverso il metodo ``handle``,
che viene chiamato per ogni plugin **attivo** passandogli il parametro
``request``, classe ``pinolo.Request`` descritta di seguito:

.. autoclass:: pinolo.Request
    :members:

Prima di tutto e' necessario verificare se il comando IRC specificato in
``request.command`` verra' gestito da questo plugin; di seguito e' riportato
l'esempio di un metodo ``handle`` che gestisce il comando IRC **prcd**.
In questo metodo ``handle`` viene anche utilizzata la libreria ``getopt`` per
gestire le opzioni in stile *linea di comando* del comando IRC; la soluzione
utilizzata, poco elegante, e' quella di gestire l'*Exception*
``OptionParserError`` e riportare direttamente l'errore all'utente, o in caso di
opzioni valide, chiamare il metodo che gestisce il comando, passandogli le
variabili ``request``, ``options`` e ``args``.

::

    def handle(self, request):
        if request.command in [ 'prcd' ]:
            try:
                (options, args) = self.prcd_opt.parse_args(request.arguments)
            except OptionParserError, e:
                request.reply(str(e))
            else:
                self.simple_prcd(request, options, args)

Un metodo per gestire finalmente il comando sara' tipo il seguente; il parametro
``options`` viene usato per verificare la presenza di opzioni, mentre
``request.reply`` viene utilizzato per rispondere in maniera *smart* a chi ha
chiamato il comando IRC (*smart* perche' ``reply`` rispondera' pubblicamente in
canale per le richieste pubbliche, e in query per le richieste private).

::

    def simple_prcd(self, request, options, args):
        moccolo = None

        if options.category:
            if not options.category in self.prcd_db:
                request.reply("Categoria non trovata :(")
                return

            moccolo = random.choice(self.prcd_db[options.category])

        else:
            category = random.choice(self.prcd_db.keys())
            moccolo = random.choice(self.prcd_db[category])
            moccolo = "%s, %s" % (category, moccolo)

        request.reply(moccolo)

.. warning::

    Il testo inviato su IRC con le chiamate a ``request.reply`` **non** deve
    essere ``Unicode``.


Segnali
=======
I plugin di pinolo possono anche fare uso di un sistema di segnali implementato
grazie alla libreria PyPubSub_::

    from twisted.python import log
    from pubsub import Publisher as pubsub

In questo esempio il plugin salva dei nuovi dati nel database e invia il segnale
``get_quote`` passando come parametro ``data`` i suddetti dati (ehm)::

    pubsub.sendMessage('add_quote', data=result)

Un plugin puo' *ascoltare* uno o piu' segnali chiamando il metodo
``subscribe``::

    pubsub.subscribe(self.add_quote_signal, 'add_quote')

    def add_quote_signal(self, event):
        log.msg("Adding a quote from a signal")
        self.add_quote(event.data)

.. _Yapsy:  http://pypi.python.org/pypi/Yapsy/
.. _PyPubSub: http://pypi.python.org/pypi/PyPubSub
