from rest_framework import permissions

class IsRoleAuthorized(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # 1. Superadmin has full access
        if user.role == 'superadmin' or user.is_superuser:
            return True
            
        # 2. Manager has full access to objects in their store
        if user.role == 'manager':
            # check if obj has store
            if hasattr(obj, 'store') and obj.store == user.store:
                return True
            # For objects like Users which have a store
            if obj.__class__.__name__ == 'User' and obj.store == user.store:
                return True
            return False
            
        # 3. Senior Seller
        if user.role == 'senior_seller':
            # Always allow read
            if request.method in permissions.SAFE_METHODS:
                return True
                
            model_name = obj.__class__.__name__
            
            # CRUD sales, CRUD products
            if model_name in ['Sale', 'SaleItem', 'Products', 'Variant', 'Size', 'SizeScale']:
                return True
                
            # C clients, C payment, C cash, C debt (Edit/Delete only if created by them)
            if model_name in ['Client', 'PaymentMenthod', 'Cash', 'Debt']:
                if hasattr(obj, 'created_by') and obj.created_by == user:
                    return True
                if hasattr(obj, 'user') and obj.user == user:
                    return True
                if hasattr(obj, 'seller') and obj.seller == user:
                    return True
                return False
                
            return False
            
        # 4. Junior Seller
        if user.role == 'junior_seller':
            if request.method in permissions.SAFE_METHODS:
                return True
                
            # C sales, C products, C cash, C debt (Edit/Delete only if created by them)
            # This applies to everything for Junior seller
            if hasattr(obj, 'created_by') and obj.created_by == user:
                return True
            if hasattr(obj, 'user') and obj.user == user:
                return True
            if hasattr(obj, 'seller') and obj.seller == user:
                return True
                
            return False
            
        return False
