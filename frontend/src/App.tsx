import { useState } from 'react';
import type { SupportedProduct, GuideRequest, GuideResponse } from './types';
import { ProductSelector } from './components/ProductSelector';
import { RoleConfigurator } from './components/RoleConfigurator';
import { GenerationView } from './components/GenerationView';
import { GuideViewer } from './components/GuideViewer';

type AppPage = 'select' | 'configure' | 'generating' | 'viewing';

export default function App() {
  const [page, setPage] = useState<AppPage>('select');
  const [selectedProduct, setSelectedProduct] = useState<SupportedProduct | null>(null);
  const [completedGuide, setCompletedGuide] = useState<GuideResponse | null>(null);

  function handleProductSelect(product: SupportedProduct) {
    setSelectedProduct(product);
    setPage('configure');
  }

  function handleGenerate(_request: GuideRequest) {
    setPage('generating');
  }

  function handleGenerationComplete(guide: GuideResponse) {
    setCompletedGuide(guide);
    setPage('viewing');
  }

  function handleBackToStart() {
    setPage('select');
    setSelectedProduct(null);
    setCompletedGuide(null);
  }

  return (
    <div className="min-h-screen bg-[#fafafa] flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shrink-0">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1
              className="text-lg font-semibold text-slate-900 cursor-pointer"
              onClick={handleBackToStart}
            >
              OnboardIQ
            </h1>
            <span className="hidden sm:block text-xs text-slate-400 border-l border-slate-200 pl-3">
              AI-Powered Onboarding Guide Generator
            </span>
          </div>
          <div className="flex items-center gap-2">
            {page !== 'select' && (
              <span className="text-xs text-slate-400">
                {page === 'configure' && 'Configure'}
                {page === 'generating' && 'Generating...'}
                {page === 'viewing' && 'Viewing Guide'}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {page === 'select' && (
          <div className="py-16 px-6">
            <ProductSelector onSelect={handleProductSelect} />
          </div>
        )}

        {page === 'configure' && selectedProduct && (
          <div className="py-10 px-6">
            <RoleConfigurator
              product={selectedProduct as 'stripe'}
              onGenerate={handleGenerate}
              onBack={() => setPage('select')}
            />
          </div>
        )}

        {page === 'generating' && (
          <div className="py-10 px-6">
            <GenerationView onComplete={handleGenerationComplete} />
          </div>
        )}

        {page === 'viewing' && completedGuide && (
          <GuideViewer guide={completedGuide} onBack={handleBackToStart} />
        )}
      </main>

      {/* Footer */}
      {page !== 'viewing' && (
        <footer className="bg-white border-t border-slate-200 shrink-0">
          <div className="max-w-7xl mx-auto px-6 h-10 flex items-center justify-center">
            <p className="text-xs text-slate-400">
              Powered by Claude + LangChain + LangGraph
            </p>
          </div>
        </footer>
      )}
    </div>
  );
}
