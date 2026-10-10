import { useState } from 'react';
import { HeartHandshake, CheckCircle2, XCircle, MapPin, Truck, ThermometerSnowflake, FileText, Sparkles } from 'lucide-react';

export default function DonationCentresView() {
  const [itemName, setItemName] = useState('Leftover Steamed Rice');
  const [quantity, setQuantity] = useState(6.5);
  const [isCooked, setIsCooked] = useState(true);
  const [requiresColdChain, setRequiresColdChain] = useState(true);
  const [useAI, setUseAI] = useState(false);
  const [matched, setMatched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [matches, setMatches] = useState<any[]>([]);
  const [handoverModalOpen, setHandoverModalOpen] = useState(false);

  const handleMatch = () => {
    setIsSearching(true);
    setMatched(false);
    
    // Simulate API Call to /api/donations/match?use_ai={useAI}
    setTimeout(() => {
      let results = [];
      if (useAI) {
        results = [
          {
            centre: {
              name: 'Feeding India - Pune Chapter (AI Discovered)',
              contact_person: 'Local Admin',
              phone: '9876541111',
              address: 'Kalyani Nagar, Pune',
              pickup_service_available: true,
              verified: false
            },
            is_eligible: true,
            match_score: 90,
            distance_km: 3.2,
            eligibility_notes: ['Fully eligible.', '⚠️ AI-Sourced: Manager must verify food safety protocols manually.']
          },
          {
            centre: {
              name: 'Savitribai Phule Orphanage (AI Discovered)',
              contact_person: 'Admin',
              address: 'Hadapsar, Pune',
              pickup_service_available: false,
              verified: false
            },
            is_eligible: true,
            match_score: 82,
            distance_km: 6.5,
            eligibility_notes: ['Fully eligible.', '⚠️ AI-Sourced: Manager must verify food safety protocols manually.']
          }
        ];
      } else {
        results = [
          {
            centre: {
              name: 'Pune Food Bank',
              contact_person: 'Amit Deshmukh',
              phone: '9876543210',
              address: 'Shivaji Nagar, Pune',
              pickup_service_available: true,
              verified: true
            },
            is_eligible: true,
            match_score: 95,
            distance_km: 8.4,
            eligibility_notes: ['Fully eligible.']
          },
          {
            centre: {
              name: 'Robin Hood Army - Kharadi',
              contact_person: 'Priya Sharma',
              address: 'Kharadi, Pune',
              pickup_service_available: false,
              verified: true
            },
            is_eligible: true,
            match_score: 85,
            distance_km: 1.2,
            eligibility_notes: ['Fully eligible.']
          }
        ];
      }
      setMatches(results);
      setIsSearching(false);
      setMatched(true);
    }, useAI ? 3000 : 800); // AI takes longer
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Donation Centre Matching</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Match Form */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 flex flex-col h-fit">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Surplus Details</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Item Name</label>
              <input 
                type="text" 
                value={itemName}
                onChange={(e) => setItemName(e.target.value)}
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:ring-restaurant-primary focus:border-restaurant-primary"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Quantity (kg)</label>
              <input 
                type="number" 
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:ring-restaurant-primary focus:border-restaurant-primary"
              />
            </div>
            
            <div className="flex items-center space-x-2 pt-2">
              <input 
                type="checkbox" 
                id="cooked" 
                checked={isCooked}
                onChange={(e) => setIsCooked(e.target.checked)}
                className="rounded border-slate-300 text-restaurant-primary focus:ring-restaurant-primary"
              />
              <label htmlFor="cooked" className="text-sm text-slate-700">This is prepared/cooked food</label>
            </div>
            
            <div className="flex items-center space-x-2">
              <input 
                type="checkbox" 
                id="cold" 
                checked={requiresColdChain}
                onChange={(e) => setRequiresColdChain(e.target.checked)}
                className="rounded border-slate-300 text-restaurant-primary focus:ring-restaurant-primary"
              />
              <label htmlFor="cold" className="text-sm text-slate-700 flex items-center">
                <ThermometerSnowflake className="w-4 h-4 mr-1 text-sky-500" />
                Requires strict cold-chain (&lt;4°C)
              </label>
            </div>
          </div>
          
          <div className="mt-6 pt-4 border-t border-slate-200">
             <div className="flex items-center justify-between">
                <label htmlFor="ai-toggle" className="text-sm font-medium text-indigo-900 flex items-center">
                  <Sparkles className="w-4 h-4 mr-2 text-indigo-600" />
                  Gemini Live Discovery
                </label>
                <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                    <input type="checkbox" id="ai-toggle" checked={useAI} onChange={(e)=>setUseAI(e.target.checked)} className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer border-slate-300 checked:border-indigo-600 checked:right-0 checked:bg-indigo-600 transition-all duration-200"/>
                    <label htmlFor="ai-toggle" className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer ${useAI ? 'bg-indigo-200' : 'bg-slate-300'}`}></label>
                </div>
             </div>
             <p className="text-xs text-slate-500 mt-2">When enabled, Gemini dynamically searches the web for nearby active NGOs instead of using our internal database.</p>
          </div>

          <button 
            onClick={handleMatch}
            disabled={isSearching}
            className="mt-6 w-full bg-restaurant-primary text-white py-2 rounded-md hover:bg-emerald-700 font-medium transition-colors flex justify-center items-center disabled:bg-emerald-400">
            {isSearching ? 'Searching...' : (
              <><HeartHandshake className="w-4 h-4 mr-2" /> Find Verified Matches</>
            )}
          </button>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-4">
          {isSearching ? (
             <div className="h-64 border-2 border-dashed border-slate-200 rounded-lg flex flex-col items-center justify-center text-center p-8 bg-slate-50">
               <div className="animate-spin w-8 h-8 border-4 border-restaurant-primary border-t-transparent rounded-full mb-4"></div>
               <h3 className="text-lg font-medium text-slate-900 mb-2">
                 {useAI ? 'Gemini is scanning the web for NGOs...' : 'Matching with database...'}
               </h3>
             </div>
          ) : !matched ? (
            <div className="h-64 border-2 border-dashed border-slate-200 rounded-lg flex flex-col items-center justify-center text-center p-8 bg-slate-50">
              <HeartHandshake className="w-12 h-12 text-slate-300 mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">Ready to Donate?</h3>
              <p className="text-slate-500 max-w-md text-sm">Enter the details of your safe surplus food to find verified NGOs and food banks in your area that can accept it.</p>
            </div>
          ) : (
            matches.map((match, idx) => (
              <div key={idx} className={`bg-white rounded-lg shadow-sm border p-6 flex flex-col sm:flex-row gap-6 ${match.is_eligible ? (match.centre.verified ? 'border-emerald-200' : 'border-indigo-200') : 'border-slate-200 opacity-60'}`}>
                <div className="flex-1">
                  <div className="flex items-center mb-2">
                    <h3 className="text-lg font-bold text-slate-900 mr-3">{match.centre.name}</h3>
                    {match.is_eligible ? (
                      match.centre.verified ? (
                         <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800 flex items-center">
                           <CheckCircle2 className="w-3 h-3 mr-1" /> Verified Match
                         </span>
                      ) : (
                         <span className="px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800 flex items-center">
                           <Sparkles className="w-3 h-3 mr-1" /> AI Discovered
                         </span>
                      )
                    ) : (
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-rose-100 text-rose-800 flex items-center">
                        <XCircle className="w-3 h-3 mr-1" /> Ineligible
                      </span>
                    )}
                  </div>
                  
                  <div className="space-y-2 mb-4 text-sm text-slate-600">
                    <div className="flex items-center">
                      <MapPin className="w-4 h-4 mr-2 text-slate-400" />
                      {match.centre.address} ({match.distance_km} km away)
                    </div>
                    {match.is_eligible && (
                      <div className="flex items-center">
                        <Truck className={`w-4 h-4 mr-2 ${match.centre.pickup_service_available ? 'text-emerald-500' : 'text-amber-500'}`} />
                        {match.centre.pickup_service_available ? 'Pickup service available' : 'Drop-off required'}
                      </div>
                    )}
                  </div>
                  
                  <div className="text-sm">
                    <span className="font-semibold text-slate-700">Notes: </span>
                    <span className={match.is_eligible ? (match.centre.verified ? 'text-slate-600' : 'text-indigo-600 font-medium') : 'text-rose-600'}>
                      {match.eligibility_notes.map((n: string, i: number) => (
                        <div key={i}>{n}</div>
                      ))}
                    </span>
                  </div>
                </div>
                
                <div className="flex flex-col justify-center border-t sm:border-t-0 sm:border-l border-slate-200 pt-4 sm:pt-0 sm:pl-6 w-full sm:w-48">
                  {match.is_eligible && (
                    <button 
                      onClick={() => setHandoverModalOpen(true)}
                      className="w-full bg-restaurant-secondary text-white px-4 py-2 rounded-md hover:bg-amber-700 font-medium text-sm transition-colors mb-2">
                      Record Handover
                    </button>
                  )}
                  <button 
                    disabled={!match.is_eligible}
                    className={`w-full px-4 py-2 rounded-md font-medium text-sm transition-colors border ${match.is_eligible ? 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50' : 'bg-slate-50 border-slate-200 text-slate-400 cursor-not-allowed'}`}>
                    View Details
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {handoverModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full m-4">
            <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center">
              <FileText className="w-5 h-5 mr-2 text-restaurant-primary" />
              Log Handover Record
            </h2>
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Driver / Receiver Name</label>
                <input type="text" className="w-full border border-slate-300 rounded-md px-3 py-2 focus:ring-restaurant-primary" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Temperature at Handover (°C)</label>
                <input type="number" className="w-full border border-slate-300 rounded-md px-3 py-2 focus:ring-restaurant-primary" />
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button 
                onClick={() => setHandoverModalOpen(false)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-md font-medium text-sm">
                Cancel
              </button>
              <button 
                onClick={() => setHandoverModalOpen(false)}
                className="px-4 py-2 bg-restaurant-primary text-white hover:bg-emerald-700 rounded-md font-medium text-sm">
                Confirm Handover
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
