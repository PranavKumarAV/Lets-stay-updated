import { useState } from "react";
import { Button } from "@/components/ui/button";
import { UserPreferences } from "@/pages/home";

interface RegionSelectionProps {
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  onNext: () => void;
}

export function RegionSelection({ preferences, updatePreferences, onNext }: RegionSelectionProps) {
  const [selectedRegion, setSelectedRegion] = useState(preferences.region);
  const [selectedCountry, setSelectedCountry] = useState(preferences.country || "");

  const handleRegionSelect = (region: string) => {
    setSelectedRegion(region);
    updatePreferences({ region });
    if (region === "international") {
      setSelectedCountry("");
      updatePreferences({ country: "" });
    }
  };

  const handleCountrySelect = (country: string) => {
    setSelectedCountry(country);
    updatePreferences({ country });
  };

  const canProceed = selectedRegion && (selectedRegion === "international" || selectedCountry);

  return (
    <div>
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-secondary mb-4">Choose Your News Region</h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Select whether you want to stay updated with international news or focus on a specific country's coverage.
        </p>
      </div>

      <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-6">
        {/* International Option */}
        <div
          className={`group cursor-pointer transition-all duration-300 hover:scale-105 ${
            selectedRegion === "international" ? "ring-2 ring-primary" : ""
          }`}
          onClick={() => handleRegionSelect("international")}
        >
          <div
            className={`bg-surface rounded-2xl p-8 shadow-lg border transition-colors ${
              selectedRegion === "international"
                ? "border-primary bg-blue-50"
                : "border-gray-200 hover:border-primary hover:shadow-xl"
            }`}
          >
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-globe text-primary text-2xl"></i>
              </div>
              <h3 className="text-xl font-semibold text-secondary mb-2">International News</h3>
              <p className="text-gray-600 mb-6">
                Get the latest updates from around the world with global perspective and coverage.
              </p>
              <div className="space-y-2 text-sm text-gray-500">
                <div className="flex items-center justify-center space-x-2">
                  <i className="fas fa-check text-success"></i>
                  <span>Global coverage</span>
                </div>
                <div className="flex items-center justify-center space-x-2">
                  <i className="fas fa-check text-success"></i>
                  <span>Multiple perspectives</span>
                </div>
                <div className="flex items-center justify-center space-x-2">
                  <i className="fas fa-check text-success"></i>
                  <span>Breaking international news</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Country-Specific Option */}
        <div
          className={`group cursor-pointer transition-all duration-300 hover:scale-105 ${
            selectedRegion === "country" ? "ring-2 ring-primary" : ""
          }`}
          onClick={() => handleRegionSelect("country")}
        >
          <div
            className={`bg-surface rounded-2xl p-8 shadow-lg border transition-colors ${
              selectedRegion === "country"
                ? "border-primary bg-blue-50"
                : "border-gray-200 hover:border-primary hover:shadow-xl"
            }`}
          >
            <div className="text-center">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-flag text-accent text-2xl"></i>
              </div>
              <h3 className="text-xl font-semibold text-secondary mb-2">Country-Specific News</h3>
              <p className="text-gray-600 mb-4">
                Focus on news and updates from a specific country with local context and relevance.
              </p>


              {/* Country Selector */}
              {selectedRegion === "country" && (
                <div className="mb-6" onClick={(e) => e.stopPropagation()}>
                  <select 
                    value={selectedCountry} 
                    onChange={(e) => handleCountrySelect(e.target.value)}
                    className="w-full h-10 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Select a country...</option>
                    {/* Offer all countries supported by the NewsAPI.  Each option uses the
                       official two‑letter ISO 3166‑1 alpha‑2 code as the value.  The
                       NewsAPI will filter top headlines based on these codes for
                       country‑specific searches.  See https://newsapi.org/docs/endpoints/top-headlines */}
                    <option value="AE">United Arab Emirates</option>
                    <option value="AR">Argentina</option>
                    <option value="AT">Austria</option>
                    <option value="AU">Australia</option>
                    <option value="BE">Belgium</option>
                    <option value="BG">Bulgaria</option>
                    <option value="BR">Brazil</option>
                    <option value="CA">Canada</option>
                    <option value="CH">Switzerland</option>
                    <option value="CN">China</option>
                    <option value="CO">Colombia</option>
                    <option value="CU">Cuba</option>
                    <option value="CZ">Czech Republic</option>
                    <option value="DE">Germany</option>
                    <option value="EG">Egypt</option>
                    <option value="FR">France</option>
                    <option value="GB">United Kingdom</option>
                    <option value="GR">Greece</option>
                    <option value="HK">Hong Kong</option>
                    <option value="HU">Hungary</option>
                    <option value="ID">Indonesia</option>
                    <option value="IE">Ireland</option>
                    <option value="IL">Israel</option>
                    <option value="IN">India</option>
                    <option value="IT">Italy</option>
                    <option value="JP">Japan</option>
                    <option value="KR">South Korea</option>
                    <option value="LT">Lithuania</option>
                    <option value="LV">Latvia</option>
                    <option value="MA">Morocco</option>
                    <option value="MX">Mexico</option>
                    <option value="MY">Malaysia</option>
                    <option value="NG">Nigeria</option>
                    <option value="NL">Netherlands</option>
                    <option value="NO">Norway</option>
                    <option value="NZ">New Zealand</option>
                    <option value="PH">Philippines</option>
                    <option value="PL">Poland</option>
                    <option value="PT">Portugal</option>
                    <option value="RO">Romania</option>
                    <option value="RS">Serbia</option>
                    <option value="RU">Russia</option>
                    <option value="SA">Saudi Arabia</option>
                    <option value="SE">Sweden</option>
                    <option value="SG">Singapore</option>
                    <option value="SI">Slovenia</option>
                    <option value="SK">Slovakia</option>
                    <option value="TH">Thailand</option>
                    <option value="TR">Turkey</option>
                    <option value="TW">Taiwan</option>
                    <option value="UA">Ukraine</option>
                    <option value="US">United States</option>
                    <option value="VE">Venezuela</option>
                    <option value="ZA">South Africa</option>
                  </select>
                </div>
              )}

              <div className="space-y-2 text-sm text-gray-500">
                <div className="flex items-center justify-center space-x-2">
                  <i className="fas fa-check text-success"></i>
                  <span>Local context</span>
                </div>
                <div className="flex items-center justify-center space-x-2">
                  <i className="fas fa-check text-success"></i>
                  <span>Regional relevance</span>
                </div>
                <div className="flex items-center justify-center space-x-2">
                  <i className="fas fa-check text-success"></i>
                  <span>Country-specific sources</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="text-center mt-8">
        <Button
          onClick={onNext}
          disabled={!canProceed}
          className="bg-primary text-white px-8 py-3 font-medium hover:bg-blue-700"
        >
          Continue to Topics
          <i className="fas fa-arrow-right ml-2"></i>
        </Button>
      </div>
    </div>
  );
}
