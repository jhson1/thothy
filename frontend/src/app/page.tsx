"use client";

import React, { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Header from "@/components/Header";
import AgentHub from "@/components/AgentHub";
import MyAgents from "@/components/MyAgents";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Copy, Check } from "lucide-react";

// Define pricing policy type
interface PricingPolicy {
  id: string;
  name: string;
  monthly_price: number | 'custom';
  features: {
    access_to_agents: string;
    usage_limits: string;
    response_speed: string;
    ai_model_quality: string;
    dedicated_hardware: string;
    premium_models: string;
    on_premises: string;
    custom_agents: string;
    custom_ui_support: string;
    integrate_own_models: string;
  };
}

// Hardcoded pricing policies based on the provided table
const PRICING_POLICIES: PricingPolicy[] = [
  {
    id: "personal",
    name: "Personal",
    monthly_price: 0,
    features: {
      access_to_agents: "Yes – all 10 agents included (Research, Report, etc.)",
      usage_limits: "Yes (up to ~100 queries/month)",
      response_speed: "Standard (slower)",
      ai_model_quality: "Basic model (entry-level LLM)",
      dedicated_hardware: "No (shared resources)",
      premium_models: "No",
      on_premises: "Not available",
      custom_agents: "No",
      custom_ui_support: "Standard support",
      integrate_own_models: "No"
    }
  },
  {
    id: "business",
    name: "Business",
    monthly_price: 950,
    features: {
      access_to_agents: "Yes – all 10 agents included",
      usage_limits: "No (Unlimited*)",
      response_speed: "Fast (priority speed)",
      ai_model_quality: "Advanced open-source models",
      dedicated_hardware: "Yes (1 dedicated GPU)",
      premium_models: "Optional add-on (pay-as-you-go at $8.5/1M tokens)",
      on_premises: "Not available",
      custom_agents: "No",
      custom_ui_support: "Standard support",
      integrate_own_models: "No"
    }
  },
  {
    id: "enterprise",
    name: "Enterprise",
    monthly_price: 'custom',
    features: {
      access_to_agents: "Yes – all 10 agents included",
      usage_limits: "No (Unlimited*)",
      response_speed: "Fastest (custom optimized)",
      ai_model_quality: "Best available (open-source + any custom models)",
      dedicated_hardware: "Yes (flexible – multiple or on-prem hardware)",
      premium_models: "Yes (included or negotiated as part of contract)",
      on_premises: "Yes (on-prem or private cloud option)",
      custom_agents: "Yes (included; tailor-made agents)",
      custom_ui_support: "Yes (custom UI branding; priority support)",
      integrate_own_models: "Yes (can incorporate client's models)"
    }
  }
];

export default function Home() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, signIn, loading } = useAuth();
  const [currentView, setCurrentView] = useState("landing");
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [contactDialogOpen, setContactDialogOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const salesEmail = "ai.thothy@gmail.com";

  useEffect(() => {
    // Check if user has previously acknowledged the notice
    const hasAcknowledged = localStorage.getItem("thothyNoticeAcknowledged");
    if (!hasAcknowledged) {
      setOpenSnackbar(true);
    }
  }, []);

  const handleGetStarted = () => {
    if (user) {
      router.push("/agent");
    } else {
      signIn();
    }
  };

  const handleCloseSnackbar = (
    event: React.SyntheticEvent | Event,
    reason?: string
  ) => {
    if (reason === "clickaway") {
      return;
    }
    setOpenSnackbar(false);
  };

  const handleAcknowledgeNotice = (acknowledge: boolean) => {
    if (acknowledge) {
      localStorage.setItem("thothyNoticeAcknowledged", "true");
    }
    setOpenSnackbar(false);
  };

  const handleCopyEmail = () => {
    navigator.clipboard.writeText(salesEmail);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };



  return (
    <div className="flex flex-col min-h-screen">
      <Header currentView="find" />

      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-r from-purple-500 to-indigo-600 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div>
              <h1 className="text-4xl md:text-5xl font-bold mb-3">
                Your Personal AI Assistant
              </h1>
              <p className="text-lg opacity-90 mb-4">
                Meet Thothy - your friendly AI companion that helps you get
                things done faster and smarter. No complex tech talk, just
                simple solutions for your daily tasks.
              </p>
              <Button
                onClick={handleGetStarted}
                disabled={loading}
                variant="default"
                size="lg"
              >
                {loading ? (
                  <div className="flex items-center">
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-indigo-600"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <title>Loading</title>
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Checking...
                  </div>
                ) : (
                  "Get Started"
                )}
              </Button>
            </div>
            <div className="hidden md:block">
              <img
                src="/hero-image.png"
                alt="Thothy AI Assistant"
                className="w-full max-w-md mx-auto"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Why Choose Thothy?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold mb-2">Smart & Simple</h3>
              <p className="text-gray-600">
                No tech jargon here! Thothy speaks your language and helps you
                accomplish tasks without the complexity.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold mb-2">Always Learning</h3>
              <p className="text-gray-600">
                The more you use Thothy, the better it gets at understanding
                your needs and preferences.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold mb-2">Your Time Saver</h3>
              <p className="text-gray-600">
                Let Thothy handle the routine tasks while you focus on what
                matters most to you.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gray-100 py-16">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
            Join thousands of users who are already experiencing the power of
            Thothy.
          </p>
          <Button
            onClick={handleGetStarted}
            disabled={loading}
            variant="default"
            size="lg"
          >
            {loading ? (
              <div className="flex items-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <title>Loading</title>
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Checking...
              </div>
            ) : (
              "Try Thothy Now"
            )}
          </Button>
        </div>
      </div>

      {/* Pricing Section */}
      <div className="py-16">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">Pricing</h2>
          
          {/* Pricing Comparison Table */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full">
                {/* Header */}
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left p-6 font-medium text-gray-900 bg-gray-50">Feature</th>
                    {PRICING_POLICIES.map((policy) => (
                      <th key={policy.id} className={`text-center p-6 min-w-[250px] ${
                        policy.name === 'Business' ? 'bg-indigo-50 border-l-2 border-r-2 border-indigo-200' : 
                        policy.name === 'Personal' ? 'bg-gray-100 opacity-75' : 'bg-gray-50'
                      }`}>
                        <div className="space-y-2">
                          {policy.name === 'Business' && (
                            <div className="bg-indigo-500 text-white px-3 py-1 rounded-full text-sm font-medium inline-block">
                              Most Popular
                            </div>
                          )}
                          {policy.name === 'Personal' && (
                            <div className="bg-gray-400 text-white px-3 py-1 rounded-full text-sm font-medium inline-block">
                              Coming Soon
                            </div>
                          )}
                          <div className={`text-xl font-bold ${policy.name === 'Personal' ? 'text-gray-500' : 'text-gray-900'}`}>
                            {policy.name}
                          </div>
                          {policy.monthly_price === 'custom' ? (
                            <div className="text-2xl font-bold text-gray-900">Custom</div>
                          ) : policy.monthly_price === 0 ? (
                            <div className={`text-2xl font-bold ${policy.name === 'Personal' ? 'text-gray-500' : 'text-gray-900'}`}>
                              Free
                            </div>
                          ) : (
                            <div className="text-2xl font-bold text-gray-900">
                              ${policy.monthly_price}
                              <span className="text-base font-normal text-gray-600">/month</span>
                            </div>
                          )}
                          <div className="pt-2">
                            <Button
                              onClick={() => policy.name !== 'Personal' && setContactDialogOpen(true)}
                              variant={policy.name === 'Business' ? 'default' : 'outline'}
                              size="sm"
                              className="w-full max-w-[180px]"
                              disabled={policy.name === 'Personal'}
                            >
                              {policy.name === 'Personal' ? 'Coming Soon' : 'Contact Sales'}
                            </Button>
                          </div>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>

                {/* Body */}
                <tbody>
                  {/* Access & Limits Section */}
                  <tr className="border-b border-gray-100">
                    <td colSpan={4} className="p-4 bg-gray-100 font-semibold text-gray-900">
                      Access & Limits
                    </td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Access to All 10 AI Agents</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        <div className="flex justify-center items-center">
                          <Check className={`w-4 h-4 mr-2 ${policy.name === 'Personal' ? 'text-gray-400' : 'text-green-500'}`} />
                          <span>{policy.features.access_to_agents}</span>
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Usage Limits</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.usage_limits}
                      </td>
                    ))}
                  </tr>

                  {/* Performance Section */}
                  <tr className="border-b border-gray-100">
                    <td colSpan={4} className="p-4 bg-gray-100 font-semibold text-gray-900">
                      Performance
                    </td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Response Speed</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.response_speed}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">AI Model Quality</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.ai_model_quality}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Dedicated AI Hardware</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.dedicated_hardware}
                      </td>
                    ))}
                  </tr>

                  {/* Advanced Features Section */}
                  <tr className="border-b border-gray-100">
                    <td colSpan={4} className="p-4 bg-gray-100 font-semibold text-gray-900">
                      Advanced Features
                    </td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Access to Premium Models</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.premium_models}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">On-Premises Deployment</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.on_premises}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Custom Agent Development</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.custom_agents}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Custom UI & Support</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.custom_ui_support}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="p-4 font-medium text-gray-900">Integrate Own AI Models</td>
                    {PRICING_POLICIES.map((policy) => (
                      <td key={policy.id} className={`p-4 text-center text-sm ${
                        policy.name === 'Business' ? 'bg-indigo-50/30' : 
                        policy.name === 'Personal' ? 'bg-gray-100/50 text-gray-500' : ''
                      }`}>
                        {policy.features.integrate_own_models}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <div className="mt-8 text-center text-sm text-gray-600">
            <p>* Unlimited usage subject to fair use policy and hardware limitations.</p>
          </div>
        </div>
      </div>

      {/* Disclaimer Snackbar */}
      {openSnackbar && (
        <AlertDialog>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Disclaimer</AlertDialogTitle>
              <AlertDialogDescription>
                This is an experimental project with AI agents. Performance may
                vary and content is not guaranteed to be accurate.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => handleAcknowledgeNotice(false)}>
                Dismiss
              </AlertDialogCancel>
              <AlertDialogAction onClick={() => handleAcknowledgeNotice(true)}>
                Don't show again
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {/* Contact Sales Dialog */}
      <AlertDialog open={contactDialogOpen} onOpenChange={setContactDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Contact Sales</AlertDialogTitle>
            <AlertDialogDescription>
              <div className="flex items-center gap-2">
                <span>{salesEmail}</span>
                <button
                  onClick={handleCopyEmail}
                  className="p-1 rounded hover:bg-gray-200"
                  aria-label="Copy email address"
                  type="button"
                >
                  <Copy size={18} />
                </button>
                {copied && <span className="text-green-600 ml-2">Copied!</span>}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setContactDialogOpen(false)}>
              Close
            </AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
