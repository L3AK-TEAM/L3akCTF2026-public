# Chimney Solution
### Author: Suvoni

We are dropped onto a small street next to some two-story buildings with red-tile roofs, an unfinished (or possibly run-down) stone and brick structure which appears adjacent to a church, and a nondescript building with a tall chimney/smokestack on top. The location looks distinctly Balkan, due to reasons such as the traditional tiled roofs, conifer trees, the poles, the black-and-cream painted fence, distinctly Balkan cars, and many other details.

The name of this challenge indicates that the chimney is the key to finding this location. However, that is a bit of a red herring, as the building number (``189``) and the church provide the best geo-location filters for an overpass turbo query. The chimney acts primarily as a visual landmark to quickly verify the correct location.

The following query finds all orthodox churches in Serbia within 200m of a building numbered ``189``:
```
[out:csv(
  name,
  "name:sr",
  "name:en",
  denomination,
  "addr:city",
  "addr:place",
  "addr:municipality",
  ::type,
  ::id,
  ::lat,
  ::lon;
  true;
  ","
)][timeout:180];

area["ISO3166-1"="RS"][admin_level=2]->.serbia;

// Any building in Serbia with house number 189.
// This catches generic building=yes objects like way 1239642384.
(
  node(area.serbia)["addr:housenumber"="189"]["building"];
  way(area.serbia)["addr:housenumber"="189"]["building"];
  relation(area.serbia)["addr:housenumber"="189"]["building"];
)->.num189_buildings;

// Serbian Orthodox churches within 200 m of those buildings
(
  node(around.num189_buildings:200)
    ["amenity"="place_of_worship"]
    ["religion"="christian"]
    ["denomination"="serbian_orthodox"];

  way(around.num189_buildings:200)
    ["amenity"="place_of_worship"]
    ["religion"="christian"]
    ["denomination"="serbian_orthodox"];

  relation(around.num189_buildings:200)
    ["amenity"="place_of_worship"]
    ["religion"="christian"]
    ["denomination"="serbian_orthodox"];
);

out center qt;
```

It returns around 10 results, one of which is our given location: Црква Cветог Луке (Crkva Svetog Luke), Vučačka, Smederevo, Serbia

[Challenge location](https://maps.app.goo.gl/fEmtC7YEz3D1AeL29)

Flag: ``L3AK{tH3_cHiMN3y_w45_a_Sm0Ke5cr3EN}``
