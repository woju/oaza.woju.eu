var OSM3SPrefix = 'https://overpass-api.de/api/';

var markerOptions = {
    weight: 4,
    color: '#03f',
};

var borderOptions = {
    weight: 2,
    color: '#03f',
    opacity: 0.3,
    fillOpacity: 0.15,
}

function createMapnikMap(id) {
    var map = L.map(id);

    L.control.layers({
        'Mapnik': L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '<a href="http://www.openstreetmap.org/">OpenStreetMap contributors</a>'
        }).addTo(map),
        'Outdoors': L.tileLayer('http://{s}.tile.thunderforest.com/outdoors/{z}/{x}/{y}.png?apikey=5507ff627c0a44dfa87e05c33176152a', {
            attribution: 'Map data: <a href="http://www.openstreetmap.org/">OpenStreetMap contributors</a>; tiles: <a href="http://thunderforest.com/">Thunderforest</a>.'
    }),
        'Ortofotomapa': L.tileLayer.wms('http://mapy.geoportal.gov.pl/wss/service/img/guest/ORTO/MapServer/WMSServer', {
            layers: 'Raster',
            attribution: '<a href="http://geoportal.gov.pl/">Geoportal.gov.pl</a>',
    }),
    }, {}).addTo(map);

    return map;
}

function addPoint(map, latlng, zoom) {

    return map;
}

function getEphemerisPopup(query) {
    return L.popup().setContent(
        '<form method="get" action="/ephemeris/' + query + '">'
        + '<table>'
        + '<tr><th><label for="first_day">Pierwszy dzień:</label></th>'
        + '<td><input type="date" '
            + 'name="first_day" '
            + 'required '
            + 'pattern="[0-9]{4}(-[0-9]{2}){2}" '
            + 'placeholder="YYYY-MM-DD"/></td></tr>'
        + '<tr><th><label for="length">Liczba dni:</label></th>'
        + '<td><input type="number" name="length" value="15" min="1" max="30"/></td></tr>'
        + '<tr><td colspan="2"><input type="submit" value="Kalendarz astronomiczny"/></td></tr></table></form>');
}

function addOSMNode(map, node, zoom) {
    var xhr = new XMLHttpRequest();
    xhr.onload = function (e) {
        var element = JSON.parse(xhr1.responseText).elements[0];
        var latlng = L.latLng(element.lat, element.lon);

        var marker = L.circleMarker(latlng, markerOptions)
            .bindPopup(getEphemerisPopup('node/' + node)).addTo(map);
        map.setView(latlng, zoom);
    };

    xhr.open('GET', OSM3SPrefix + 'interpreter?data=[out:json];node(' + node + ');out;', true);
    xhr.send();
}

function addOSMWay(map, way, maxzoom) {
    var xhr = new XMLHttpRequest();

    xhr.onload = function (e) {
        var elements = JSON.parse(xhr.responseText).elements;
        var nodes = {};
        var i;

        for (i = 1; i < elements.length; i++) {
            nodes[elements[i].id.toString()] = elements[i];
        }

        var polygon = L.polygon([], markerOptions)
            .bindPopup(getEphemerisPopup('way/' + way));

        for (i = 0; i < elements[0].nodes.length; i++) {
            var n = nodes[elements[0].nodes[i].toString()];
            polygon.addLatLng([n.lat, n.lon]);
        }

        var bounds = polygon.getBounds();
        var center = L.latLng((bounds.getNorth() + bounds.getSouth()) / 2,
            (bounds.getEast() + bounds.getWest()) / 2);
        var marker = L.circleMarker(center, markerOptions)
            .bindPopup(getEphemerisPopup('way/' + way));

        map.on('zoomend', function (e) {
            if (map.getZoom() <= 15) {
                map.addLayer(marker);
                map.removeLayer(polygon);
            } else {
                map.removeLayer(marker);
                map.addLayer(polygon);
            }
        });

        map.fitBounds(polygon.getBounds(), {maxZoom: maxzoom});
    };

    xhr.open('GET', OSM3SPrefix + 'interpreter?data=[out:json];way(' + way + ');out qt skel;node(w);out qt skel;', true);
    xhr.send();
}

function addGeoJSON(map, uri, options) {
    var xhr = new XMLHttpRequest();
    xhr.onload = function (e) {
        L.geoJson(JSON.parse(xhr.responseText), options).addTo(map);
    }

    xhr.open('GET', uri);
    xhr.send();
}
// vim:ts=4 sw=4 et
