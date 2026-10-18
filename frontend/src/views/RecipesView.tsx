import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Plus } from 'lucide-react';
import { apiRequest, type InventoryItem, type Recipe } from '../lib/api';

const inputClass = 'mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm';
const labelClass = 'block text-xs font-medium text-slate-600';

interface IngredientForm {
  ingredient_id: string;
  required_quantity: string;
  required_unit: string;
  required_stage: string;
  yield_stage_reference: string;
  servings_per_batch: string;
}

export default function RecipesView() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState({
    recipe_name: '', recipe_version: '1', serving_size: '1', serving_unit: 'portion',
    menu_category: '', selling_price: '0',
  });
  const [ingredients, setIngredients] = useState<IngredientForm[]>([{
    ingredient_id: '', required_quantity: '', required_unit: 'kg', required_stage: 'raw',
    yield_stage_reference: '', servings_per_batch: '1',
  }]);

  const refresh = useCallback(async () => {
    try {
      const [loadedRecipes, inventory] = await Promise.all([
        apiRequest<Recipe[]>('/api/recipes'),
        apiRequest<InventoryItem[]>('/api/inventory/items'),
      ]);
      setRecipes(loadedRecipes);
      setItems(inventory);
      setError('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load recipes.');
    }
  }, []);

  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);

  const updateIngredient = (index: number, key: keyof IngredientForm, value: string) => {
    setIngredients((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await apiRequest<Recipe>('/api/recipes', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          serving_size: Number(form.serving_size),
          selling_price: Number(form.selling_price),
          is_active: true,
          ingredients: ingredients.map((row) => ({
            ...row,
            required_quantity: Number(row.required_quantity),
            servings_per_batch: Number(row.servings_per_batch),
            yield_stage_reference: row.yield_stage_reference || null,
          })),
        }),
      });
      setNotice('Recipe saved.');
      setForm({ recipe_name: '', recipe_version: '1', serving_size: '1', serving_unit: 'portion', menu_category: '', selling_price: '0' });
      setIngredients([{ ingredient_id: '', required_quantity: '', required_unit: 'kg', required_stage: 'raw', yield_stage_reference: '', servings_per_batch: '1' }]);
      setShowForm(false);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save recipe.');
    } finally {
      setBusy(false);
    }
  };

  return <div className="p-8">
    <div className="mb-6 flex items-center justify-between">
      <div><h1 className="text-2xl font-bold text-slate-800">Recipe & Menu Master</h1><p className="mt-1 text-sm text-slate-500">Define recipe batches and preparation-stage ingredient quantities.</p></div>
      <button onClick={() => setShowForm((visible) => !visible)} className="rounded-md bg-restaurant-primary px-4 py-2 text-sm font-medium text-white">{showForm ? 'Close' : 'Add recipe'}</button>
    </div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    {showForm && <form onSubmit={submit} className="mb-6 space-y-5 rounded-lg border border-slate-200 bg-white p-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className={labelClass}>Recipe name<input required className={inputClass} value={form.recipe_name} onChange={(e) => setForm({ ...form, recipe_name: e.target.value })} /></label>
        <label className={labelClass}>Version<input required className={inputClass} value={form.recipe_version} onChange={(e) => setForm({ ...form, recipe_version: e.target.value })} /></label>
        <label className={labelClass}>Menu category<input required className={inputClass} value={form.menu_category} onChange={(e) => setForm({ ...form, menu_category: e.target.value })} /></label>
        <label className={labelClass}>Serving size per portion<input required type="number" min="0.001" step="any" className={inputClass} value={form.serving_size} onChange={(e) => setForm({ ...form, serving_size: e.target.value })} /></label>
        <label className={labelClass}>Serving unit<input required className={inputClass} value={form.serving_unit} onChange={(e) => setForm({ ...form, serving_unit: e.target.value })} /></label>
        <label className={labelClass}>Selling price (INR)<input required type="number" min="0" step="any" className={inputClass} value={form.selling_price} onChange={(e) => setForm({ ...form, selling_price: e.target.value })} /></label>
      </div>
      <div>
        <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold text-slate-800">Ingredients in recipe batch</h2>
          <button type="button" onClick={() => setIngredients((rows) => [...rows, { ingredient_id: '', required_quantity: '', required_unit: 'kg', required_stage: 'raw', yield_stage_reference: '', servings_per_batch: '1' }])} className="flex items-center text-sm font-medium text-indigo-700"><Plus className="mr-1 h-4 w-4" />Add ingredient</button>
        </div>
        {ingredients.map((row, index) => <div key={index} className="mb-3 grid grid-cols-1 gap-3 rounded-md border border-slate-200 p-3 sm:grid-cols-2 lg:grid-cols-6">
          <label className={labelClass}>Ingredient<select required className={inputClass} value={row.ingredient_id} onChange={(e) => {
            const item = items.find((entry) => entry.id === e.target.value);
            updateIngredient(index, 'ingredient_id', e.target.value);
            if (item) updateIngredient(index, 'required_unit', item.base_unit);
          }}><option value="">Select ingredient</option>{items.map((item) => <option key={item.id} value={item.id}>{item.item_name}</option>)}</select></label>
          <label className={labelClass}>Required quantity<input required type="number" min="0.0001" step="any" className={inputClass} value={row.required_quantity} onChange={(e) => updateIngredient(index, 'required_quantity', e.target.value)} /></label>
          <label className={labelClass}>Required unit<input required className={inputClass} value={row.required_unit} onChange={(e) => updateIngredient(index, 'required_unit', e.target.value)} /></label>
          <label className={labelClass}>Required stage<input required className={inputClass} value={row.required_stage} onChange={(e) => updateIngredient(index, 'required_stage', e.target.value)} placeholder="raw / cleaned / cooked" /></label>
          <label className={labelClass}>Yield stage reference (optional)<input className={inputClass} value={row.yield_stage_reference} onChange={(e) => updateIngredient(index, 'yield_stage_reference', e.target.value)} /></label>
          <label className={labelClass}>Servings per batch<input required type="number" min="0.001" step="any" className={inputClass} value={row.servings_per_batch} onChange={(e) => updateIngredient(index, 'servings_per_batch', e.target.value)} /></label>
        </div>)}
      </div>
      <button disabled={busy || !items.length} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? 'Saving…' : 'Save recipe'}</button>
    </form>}
    <section className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-left text-sm text-slate-600">
        <thead className="border-b bg-slate-50 text-slate-700"><tr><th className="px-5 py-3">Recipe</th><th className="px-5 py-3">Version</th><th className="px-5 py-3">Category</th><th className="px-5 py-3">Serving size</th><th className="px-5 py-3">Price</th><th className="px-5 py-3">Ingredients</th><th className="px-5 py-3">Status</th></tr></thead>
        <tbody className="divide-y divide-slate-200">{recipes.length ? recipes.map((recipe) => <tr key={recipe.recipe_id}>
          <td className="px-5 py-4 font-medium text-slate-900">{recipe.recipe_name}</td><td className="px-5 py-4">{recipe.recipe_version}</td><td className="px-5 py-4">{recipe.menu_category}</td><td className="px-5 py-4">{recipe.serving_size} {recipe.serving_unit}</td><td className="px-5 py-4">₹{recipe.selling_price}</td><td className="px-5 py-4">{recipe.ingredients.map((ingredient) => items.find((item) => item.id === ingredient.ingredient_id)?.item_name ?? ingredient.ingredient_id).join(', ')}</td><td className="px-5 py-4">{recipe.is_active ? 'Active' : 'Inactive'}</td>
        </tr>) : <tr><td colSpan={7} className="p-8 text-center">No recipes have been added.</td></tr>}</tbody>
      </table>
    </section>
  </div>;
}
