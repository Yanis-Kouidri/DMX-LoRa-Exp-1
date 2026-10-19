# Configuration d'une mote RN2483

## Configurer la mote pour ChirpStack

Lire le HWEUI de la mote, qui sert de DevEUI :

```
sys get hweui
```

Configurer la mote, en remplaçant `<HW_EUI>` par la valeur lue et
`<APPKEY_CHIRPSTACK>` par l'AppKey du device dans ChirpStack :

```
mac reset 868
mac set deveui <HW_EUI>
mac set appeui 0000000000000000
mac set appkey <APPKEY_CHIRPSTACK>
mac save
```

`mac reset 868` remet les valeurs par défaut de la bande EU868 et efface une
éventuelle configuration précédente. `mac save` conserve la configuration au
redémarrage.

Vérification :

```
mac get deveui
mac get appeui
```

## Rejoindre le réseau et envoyer un message

```
mac join otaa
mac tx uncnf 1 D93A64
```

- `mac join otaa` : join OTAA. La mote répond `ok`, puis `accepted` ou
  `denied`.
- `mac tx uncnf 1 D93A64` : uplink non confirmé sur le port 1, avec la charge
  utile `D93A64` en hexadécimal.

## Désactiver le duty cycle (environnement isolé uniquement)

⚠️ En EU868, le duty cycle (1 % sur la sous-bande 868.0-868.6 MHz) est une
obligation réglementaire. Ne le désactiver que pour des tests en milieu
parfaitement isolé (cage de Faraday, liaison câblée avec atténuateurs), jamais
sur un réseau public comme TTN.

À lancer **après** le join OTAA : le join peut ajouter des canaux (CFList) avec
leur duty cycle par défaut.

```
mac set ch dcycle 0 0
mac set ch dcycle 1 0
mac set ch dcycle 2 0
mac set dcycleps 1
```

- `mac set ch dcycle <canal> 0` : duty cycle du canal = 100 / (dcycle + 1) %,
  donc 0 = 100 %. Les canaux 0 à 2 valent 302 par défaut (0,33 % chacun).
  Répéter pour chaque canal actif (de 3 à 15) si le réseau en a ajouté
  (`mac get ch status <canal>`).
- Depuis le firmware 1.0.4, un dcycle à 0 fait aussi ignorer le duty cycle
  du join.
- `mac set dcycleps 1` : lève la limite globale que le réseau peut imposer
  via DutyCycleReq.

Vérification :

```
mac get ch dcycle 0
mac get dcycleps
```

Le script `src/disable_duty_cycle.py` fait la même chose sur les 16 canaux
et vérifie chaque valeur.

**Ne pas faire `mac save` après** : la configuration serait conservée au
redémarrage. Pour revenir à la normale, `sys reset` suffit si rien n'a été
sauvegardé. Sinon, `mac reset 868` remet les valeurs par défaut de la bande ;
il faut alors reconfigurer deveui, appeui et appkey (voir plus haut).
