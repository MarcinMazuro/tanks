# Game Design Document: Czołgi

## Wstęp
Projekt gry „Czołgi” to wieloosobowa gra zręcznościowa czasu rzeczywistego, w której gracze sterują
czołgami poruszającymi się po labiryncie zbudowanym ze ścian i przeszkód. Celem gry jest
przetrwanie i wyeliminowanie innych graczy poprzez trafienie ich pociskami, które mogą odbijać się
od ścian. Gra została zaprojektowana z użyciem architektury klient–serwer, z synchronizacją rozgrywki
w ramach stałych jednostek czasu zwanych „tickami”. W grze mogą brać udział maksymalnie cztery
osoby, a komunikacja pomiędzy klientem i serwerem realizowana jest przy użyciu protokołu UDP, co
zapewnia niskie opóźnienia i płynność gry. Zasady działania gry zostały opisane dokładniej w pierczej
części sprawozdania.

## Diagram sekwencji
Załączony diagram sekwencji przedstawia pełny przebieg interakcji między klientami (Gracze 1–4),
kolejką graczy oraz serwerem gry, od momentu dołączenia do gry aż po zakończenie rozgrywki.
Diagram ten szczegółowo obrazuje proces inicjalizacji gry oraz przebieg jednej rundy.

Etapy działania:
• Dołączanie graczy:
  o Każdy z graczy kolejno dołącza do kolejki, co jest rejestrowane przez komponent
    „Kolejka”.
  o Po dołączeniu ostatniego gracza, serwer inicjuje stworzenie nowej gry.
• Rozpoczęcie gry:
  o Serwer przesyła sygnał rozpoczęcia rozgrywki do wszystkich klientów.
  o Każdy gracz odpowiada potwierdzeniem gotowości ("Jestem gotowy").
• Główna pętla gry:
  o Serwer cyklicznie przesyła stan gry (pozycje graczy, pocisków, itp.).
  o Każdy żywy gracz wysyłaj swoje akcje (ruch, strzał, obrót) w ramach każdej iteracji
    ticka.
  o Pętla ta trwa, dopóki żyje co najmniej dwóch graczy lub nie zakończy się czas
    rozgrywki.
• Zakończenie gry:
  o Po spełnieniu warunku końca gry, serwer przesyła do wszystkich klientów wyniki
    końcowe.

## Diagram klas
Diagram przedstawia schemat gry 2D z czołgami: gracze poruszają się po mapie, strzelają pociskami,
sprawdzają kolizje z mapą oraz między sobą. Klasa Game zarządza logiką rozgrywki, Map definiuje
otoczenie, Player odpowiada za jednostki graczy, a Bullet za pociski.

**Player (Gracz)**
- Atrybuty:
  - name: String — nazwa gracza.
  - isAlive: Bool — czy gracz jest żywy.
  - position: Tuple(int, int) — pozycja gracza na mapie.
  - direction: Tuple(int, int) — kierunek, w którym gracz jest zwrócony.
  - bullets: List[Bullet] — lista pocisków gracza.
  - ipAddress: String — adres IP gracza (gra sieciowa).
- Metody:
  - fireBullet() — strzał pociskiem.
  - turnLeft() — obrót w lewo.
  - turnRight() — obrót w prawo.
  - moveForward() — ruch do przodu.
  - moveBackward() — ruch do tyłu.
  - wallCollisionCheck() — sprawdzenie kolizji ze ścianą.

**Bullet (Pocisk)**
- Atrybuty:
  - position: Tuple(int, int) — pozycja pocisku.
  - hit: Bool — czy pocisk trafił cel.
  - lifeTime: Time — czas życia pocisku.
- Metody:
  - spawnBullet(position: Tuple(int, int)) — utworzenie pocisku w danym miejscu.
  - despawnBullet() — usunięcie pocisku.
  - collisionWithPlayer(player: Player) — sprawdzenie kolizji z graczem.

**Game (Gra)**
- Atrybuty:
  - players: List[Player] — lista aktywnych graczy.
  - map: Map — mapa gry.
  - defeatedPlayers: List[Player] — lista pokonanych graczy.
- Metody:
  - drawMap() — narysowanie mapy.
  - startGame() — rozpoczęcie gry.
  - endGame() — zakończenie gry.
  - eliminatePlayer(player: Player) — eliminacja gracza.
  - spawnPlayer(player: Player) — respawnowanie gracza.

**Map (Mapa)**
- Atrybuty:
  - size: Tuple(int, int) — rozmiar mapy.
  - name: String — nazwa mapy.
  - wallsList: List[Tuple[int, int]] — lista pozycji ścian.
- Metody:
  - addWall(int, int) — dodanie ściany do mapy.

**Relacje między klasami:**
- Player ↔ Bullet: Gracze mają listę własnych pocisków.
- Game ↔ Player: Gra posiada listę graczy i listę pokonanych graczy.
- Game ↔ Map: Gra zawiera obiekt Map.
- Bullet ↔ Player: Pocisk może kolidować z graczem.

## 1 Opis gry

Czołgi to gra zręcznościowa, w której gracze sterują czołgami poruszającymi się po labiryncie utworzonym ze ścian oraz przeszkód. Celem gry jest wyeliminowanie innych graczy za pomocą pocisków oraz przetrwanie do końca rundy. Pociski mogą odbijać się od ścian, co pozwala na bardziej strategiczne zagrania. Czołgi mogą poruszać się do przodu i do tyłu oraz obracać wokół własnej osi.

*Rysunek 1: Przykładowa mapa. Kolor czarny – ściany, kolor czerwony – gracz pierwszy, kolor zielony– gracz drugi.*

### 1.1 Zasady

*   W grze jednocześnie może brać udział maksymalnie 4 graczy.
*   Każdy gracz dysponuje jednym życiem – trafienie pociskiem oznacza eliminację (również swoim własnym).
*   Gra rozpoczyna się równocześnie dla wszystkich graczy.
*   Mapa jest labiryntem.
*   Na początku gry każdy z graczy znajduje się w losowym miejscu w labiryncie.
*   Czołgi mogą się przemieszczać do przodu i do tyłu, a także obracać się wokół własnej osi.
*   Pociski mogą odbijać się od ścian oraz trafiają graczy.
*   Czołg nie może przejechać przez ściany, ale może przejeżdżać przez przeciwników.

### 1.2 Sterowanie

*   Klawisze W, S – ruch czołgu do przodu i do tyłu.
*   Klawisze A, D – obrót czołgu w lewo i prawo.
*   Klawisz Spacja – wystrzelenie pocisku.

## 2 Określenie punktów synchronizacji danych – co i kiedy i jak wysyłamy

Dane będą wysyłane na serwer co tick. Czyli serwer generuje tick i w tym momencie wysyłana jest wiadomość od klienta do serwera, a serwer to przetwarza. Dane wysyłamy przy użyciu interfejsu gniazd poprzez protokół UDP. Wysyłamy informacje na temat zamierzonego działania, a serwer po obsłużeniu wszystkich żądań w ticku odsyła graczom zaktualizowane informacje o grze takie jak plansza, aktualny stan gry (pozycje graczy, pozycje pocisków itp.)

Ticki są jednostką czasu w grze, w której wykonują się wszystkie akcje graczy. W grze Czołgi ticki powinny być przesyłane cyklicznie w regularnych odstępach czasu, co najmniej co 60 milisekund, co zapewni płynność rozgrywki i aktualność stanu gry.

Wysyłanie danych w tickach można zrealizować poprzez zastosowanie mechanizmu tzw. „spłaszczonej” architektury klient-serwer, w której każdy gracz jest równorzędnym klientem serwera. W tym przypadku każdy gracz wysyła swoje akcje do serwera, a serwer odsyła stan gry do wszystkich graczy.

Wysyłając dane, należy zadbać o to, aby wszystkie komputery miały zawsze aktualną wersję stanu gry. W tym celu po stronie serwera należy utrzymywać model gry, który będzie aktualizowany na podstawie danych otrzymywanych od klientów. Po stronie klienta natomiast należy utrzymywać lokalną kopię stanu gry, która będzie synchronizowana z serwerem za każdym razem, gdy zostanie wysłana nowa wiadomość.

Konkretnie, w ticku gracz powinien przesłać do serwera informacje o swoich akcjach, takie jak:

*   Ruch czołgu – kierunek ruchu (przód/tył) oraz obrót.
*   Wystrzelenie pocisku – informacja o oddaniu strzału wraz z pozycją czołgu i kierunkiem.

Serwer na podstawie otrzymanych informacji o akcjach gracza aktualizuje stan gry i odsyła go z powrotem do gracza. Informacje przesyłane przez serwer zawierają między innymi:

*   Pozycje wszystkich graczy na planszy.
*   Stan planszy – informacje o przeszkodach, aktywnych pociskach, zniszczeniach itp.
*   Pociski – wraz z ich pozycją, kierunkiem ruchu oraz ewentualnymi odbiciami od ścian.
*   Status gry – informacje o punktach życia graczy, zakończonych rundach itp.
*   Akcje innych graczy – informacje o działaniach przeciwników z poprzednich ticków.

Aby zweryfikować, czy przesyłane dane dotarły w całości w jednym ticku, można ustalić stały rozmiar danych, który będzie wysyłany w jednym ticku. Na przykład, jeśli wiadomość przesyłana co tick ma zawsze składać się ze 100 bajtów, to po otrzymaniu takiej wiadomości serwer może zweryfikować, czy faktycznie otrzymał 100 bajtów.

### 2.1 Dlaczego UDP a nie TCP?

UDP jest mniej niezawodny, ale jest szybszy i lepiej nadaje się do gier, które wymagają niskiego opóźnienia. W grze multiplayer nie interesuje nas, co działo się 10 ticków temu, tylko to, co dzieje się po ostatnim ticku i jakie mamy dalsze możliwości. Tak samo ruch czołgu, który nie doszedł w ticku n nie ma znaczenia w ticku n+1, w którym jest on już niemożliwy i jego rozważanie nie ma sensu (czołg mógł już nawet zostać zniszczony). Uznajemy, że w rozgrywce na poziomie np. 60 fps, utrata jednej klatki z pozostałych 60 może być tak nieznaczna, że niezauważalna dla gracza.

## 3 Co jest liczone na serwerze a co na klientach?

Po stronie serwera liczone i kontrolowane są następujące elementy:

*   Łączenie graczy – serwer musi koordynować łączenie się klientów z grą, aby upewnić się, że gra jest zawsze pełna i gracze mogą dołączać oraz opuszczać grę w dowolnym momencie.
*   Zarządzanie planszą – serwer musi kontrolować stan planszy (labiryntu) oraz zabezpieczyć ją przed manipulacjami ze strony klientów.
*   Kontrola poruszania się czołgów – serwer monitoruje ruch graczy po planszy, aby zapewnić, że nie wchodzą oni w kolizję ze ścianami oraz przeszkodami.
*   Obliczanie położenia pocisków – serwer przechowuje aktualny stan wszystkich aktywnych pocisków w grze.
*   Zarządzanie grą – serwer kontroluje warunki zwycięstwa, przetrwanie graczy oraz eliminuje tych, którzy zostali trafieni pociskiem.
*   Synchronizacja zegara – serwer kontroluje zegar gry i synchronizuje czas między klientami, aby zapewnić równoczesność gry i płynność ticków.

Po stronie klientów realizowane są następujące działania:

*   Sterowanie czołgiem – klient odpowiada za sterowanie ruchem własnego czołgu (przód/tył, obrót) oraz akcjami, np. strzałem.
*   Wizualizacja planszy i obiektów – klient odpowiada za wyświetlanie mapy, czołgów, pocisków i efektów na ekranie na podstawie danych otrzymanych z serwera.

## 4 Kto i jak decyduje o sytuacjach spornych?

*   Sytuacja, gdy więcej niż jeden gracz zostanie trafiony przez pocisk w tym samym ticku jest bardzo mało prawdopodobna, lecz nie niemożliwa. W takim wypadku każdy gracz zostanie wyeliminowany, a ich pozycja będzie uznana ex aequo.
*   Nie istnieje kolizja pomiędzy graczami, mogą zajmować tą samą pozycję
*   Gracz nie ponosi dodatkowych konsekwencji z powodu utracenia połączenia, jego postać po prostu stoi w miejscu, a gracz ma szansę na ponowne połączenie. Jednakże jest narażony na trafienie.

## 5 Bieżący stan gry i propagowanie

Bieżący stan gry jest przechowywany na serwerze gry. Serwer kontroluje stan planszy, pozycje graczy, życie graczy i wiele innych czynników, które wpływają na przebieg gry.

Bieżący stan gry jest propagowany poprzez wysyłanie danych między serwerem a klientami w grze. Serwer na bieżąco przesyła informacje o zmianach w stanie gry do wszystkich klientów w grze, aby zapewnić spójność i równoczesną grę. Każdy klient otrzymuje informacje o bieżącym stanie gry poprzez pakiet danych, który zawiera informacje o zmianach w stanie gry od ostatniego otrzymanego pakietu. Pakiet danych zawiera informacje o pozycjach graczy, ich akcjach czy zmianach na planszy. Po otrzymaniu pakietu danych, klient aktualizuje stan swojej gry zgodnie z otrzymanymi informacjami.

## 6 Architektura

Wybrana architektura to klient-serwer. Przekazuje ona sterowanie do głównej jednostki przez co odciąża klientów. Gracze wysyłają komunikaty o żądanych działaniach a serwer po zwalidowaniu żądania przekazuje informacje zwrotne w formie odesłania zaktualizowanego stanu rozgrywki.

## 7 Sekcja krytyczna

W architekturze klient-serwer sekcja krytyczna znajduje się po stronie serwera i dotyczy przetwarzania danych od graczy w ramach jednego ticka. Sekcja krytyczna obejmuje moment, w którym serwer odbiera dane od wszystkich klientów, przetwarza je i na tej podstawie aktualizuje globalny stan gry. Ponieważ wielu graczy może w tym samym czasie wysyłać swoje działania, serwer musi zapewnić, że operacje na współdzielonych zasobach – takich jak pozycje graczy, stan planszy, aktywne pociski – odbywają się w sposób atomowy i zsynchronizowany.
