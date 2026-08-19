# Government Spy 2.0 Solution
### Authors: Suvoni, OnyxCinder

We spawn into a clearly-European neighborhood with some houses in view and more interestingly, two stork nests with both birds present. One of the houses has the number ``92`` on it and the architecture looks distinctly Polish. 

Crucially, stork nests are actually tracked by several databases, including OpenStreetMap. We can write an overpass turbo query to find all buildings in Poland numbered 92 that are within 50m of at least 2 stork nests.

```
[out:csv(
  "addr:housenumber",
  "addr:street",
  "addr:city",
  "addr:place",
  building,
  name,
  ::type,
  ::id,
  ::lat,
  ::lon;
  true;
  ","
)][timeout:500];

area["ISO3166-1"="PL"][admin_level=2]->.poland;

// Stork nests in Poland
(
  nwr(area.poland)["birds_nest"="stork"];
  nwr(area.poland)["natural"="birds_nest"]["species"~"Ciconia|stork|bocian", i];
  nwr(area.poland)["natural"="birds_nest"]["name"~"bocian|stork", i];
  nwr(area.poland)["man_made"="nesting_site"]["species"~"Ciconia|stork|bocian", i];
)->.stork_nests;

// Candidate buildings numbered 92 within 50 m of at least one stork nest
(
  nwr(area.poland)(around.stork_nests:50)
    ["addr:housenumber"="92"]
    ["building"];
)->.candidate92;

// Keep only candidates with at least 2 stork nests within 50 m
foreach.candidate92->.b(
  nwr.stork_nests(around.b:50)->.near_storks;

  if (near_storks.count(nwr) >= 2) {
    .b out center qt;
  }
);
```

It only returns 2 results and the first one is our location:
```
addr:housenumber,addr:street,addr:city,addr:place,building,name,@type,@id,@lat,@lon
92,,,Zapałów,yes,,way,368174935,50.0904538,22.8706524
92,,,Krowica Hołodowska,yes,,way,368196989,50.1044429,23.2308515
```

[Challenge location](https://maps.app.goo.gl/xRf37wVaggTjg6ji6)

Flag: ``L3AK{W3_L1ve_iN_A_5T0rK_SuRvE1LL4nC3_StATE}``
