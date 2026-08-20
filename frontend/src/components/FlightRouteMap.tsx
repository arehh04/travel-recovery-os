import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix leaflet default icon issue in React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const AIRPORT_COORDS: Record<string, [number, number]> = {
  'KUL': [2.7456, 101.7099],
  'NRT': [35.7720, 140.3929],
  'HND': [35.5494, 139.7798],
  'SIN': [1.3644, 103.9915],
  'JFK': [40.6413, -73.7781],
  'LHR': [51.4700, -0.4543],
  'LAX': [33.9416, -118.4085],
  'SFO': [37.6213, -122.3790],
  'CDG': [49.0097, 2.5479],
  'DXB': [25.2532, 55.3657],
  'SYD': [-33.9399, 151.1753],
  // Fallback defaults
  'DEFAULT_ORIGIN': [40.6413, -73.7781],
  'DEFAULT_DEST': [51.4700, -0.4543],
};

interface FlightRouteMapProps {
  origin: string;
  destination: string;
}

export function FlightRouteMap({ origin, destination }: FlightRouteMapProps) {
  const originCoords = AIRPORT_COORDS[origin.toUpperCase()] || AIRPORT_COORDS['DEFAULT_ORIGIN'];
  const destCoords = AIRPORT_COORDS[destination.toUpperCase()] || AIRPORT_COORDS['DEFAULT_DEST'];

  // Calculate center of the two points
  const center: [number, number] = [
    (originCoords[0] + destCoords[0]) / 2,
    (originCoords[1] + destCoords[1]) / 2,
  ];

  return (
    <div className="w-full h-64 md:h-80 rounded-xl overflow-hidden border border-surface-variant shadow-sm z-0 relative">
      <MapContainer 
        center={center} 
        zoom={2} 
        scrollWheelZoom={false} 
        style={{ height: '100%', width: '100%', zIndex: 0 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <Marker position={originCoords} />
        <Marker position={destCoords} />
        
        {/* Draw a simple line between origin and destination */}
        <Polyline 
          positions={[originCoords, destCoords]} 
          color="#00668a" 
          weight={3} 
          dashArray="10, 10" 
          className="animate-pulse"
        />
      </MapContainer>
    </div>
  );
}
