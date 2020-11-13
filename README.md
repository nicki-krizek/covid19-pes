# PES: Proti epidemický systém - COVID-19 ČR

## Upozornění

- **Ve výpočtu mohou být chyby, za výsledky neručím**
- **Verze 0.1.0 je velice rychlý prototyp**
- **Otevřená data nejsou tak přesná, takže ani výsledné skóre nemůže být tak přesné jako od MZČR/ÚZIS**

## Situace k 12.11.2020

### Posledních 60 dní

![PES 60d 2020-11-12](img/pes_60d_2020-11-12.png)

### Posledních 235 dní

![PES 235d 2020-11-12](img/pes_235d_2020-11-12.png)

## Použití

Projekt vyžaduje Python 3 a matplotlib.

```
wget https://onemocneni-aktualne.mzcr.cz/api/v2/covid-19/testy.min.json
wget https://onemocneni-aktualne.mzcr.cz/api/v2/covid-19/osoby.min.json
./pes.py 60
```

## Metodika

- [Návod pro výpočet indexu rizika](https://koronavirus.mzcr.cz/wp-content/uploads/2020/11/Stru%C4%8Dn%C3%BD-n%C3%A1vod-pro-v%C3%BDpo%C4%8Det-indexu-rizika.pdf)
- [Tisková zpráva PES](https://koronavirus.mzcr.cz/epidemiologickou-situaci-bude-nove-znazornovat-system-hodnoceni-pes/)

## Licence

- Kód: [GPLv3+](LICENSE.txt)
- Obrázky: CC0 (public domain)
