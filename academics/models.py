from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import models
import json

META_TYPES = (
    ('number', 'Number'),
    ('string', 'String'),
    ('choice', 'Multiple Choice'),
    ('url', 'URL'),
    ('textarea', 'TextArea'),
    )

SEMESTERS = (
    ('I', 'I'),
    ('II', 'II'),
    ('III', 'III'),
    ('IV', 'IV'),
    ('V', 'V'),
    ('VI', 'VI'),
    ('VII', 'VII'),
    )

LANGUAGES = (
    ('EN', 'English'),
    ('RO', 'Romanian'),
    )


class User(models.Model):

    name = models.CharField(max_length=15)
    surname = models.CharField(max_length=31)
    email = models.EmailField()
    group = models.CharField(blank=True, max_length=15)
    photo = models.ImageField(blank=True, upload_to="photos")

    def __unicode__(self):
        return u'%s %s' % (self.name, self.surname)

'''
=== How to fill in Meta Types ===

=   key - preferably all lowercase
        - if requires more words to describe, then user underscore (_) to define 

=   data - used only for multiple choice fields
         - when using console create a JSON file
            ex: data = ["student", "alumni"]
                data = JSON.dumps(data)
         - when using the admin panel enter all variants separated with coma without any spaces
            ex: student,alumni

=   multiple - always check multilpe if it's a multiple meta type
'''


class UserMetaType(models.Model):
    key = models.CharField(max_length=31)
    type = models.CharField(max_length=31, choices=META_TYPES)
    data = models.TextField(blank=True)
    multiple = models.BooleanField()

    def __unicode__(self):
        return u'%s' % (self.key)


class UserMeta(models.Model):
    user = models.ForeignKey(User)
    meta = models.ForeignKey(UserMetaType)
    value = models.TextField()

    def __unicode__(self):
        return u'%s - %s' % (self.meta, self.value)


class Course(models.Model):
    title = models.CharField(max_length=127)
    subject_ro = models.CharField(max_length=127)
    subject_en = models.CharField(max_length=127)
    professors = models.ManyToManyField(User, blank=True, verbose_name="List of professors")
    semester = models.CharField(max_length=7, choices=SEMESTERS)
    language = models.CharField(max_length=15, choices=LANGUAGES)
    courseProject = models.BooleanField()
    labs = models.BooleanField()
    literature = models.TextField(blank=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return u'%s %s' % (self.subject_en, self.semester)


'''
====Proxy Object for User class and it's attributes====

=   Load user               user = UserExtended(user_id)

=   Load empty user         user = UserExtended()

=   Get user attributes     user.age
    returns:                string (if not multiple meta)
                            list of strings (if multiple meta)

=   Check if some attribute user.hasattr('type')
    is defined

=   Update user attributes  user.age = 25
                            user.type = ['student']
                            or
                            user.type = ['student', 'alumni'] (if multiple meta)

=   Delete user attributes  del user.age

=   Delete user and all     del user
    its meta
'''


# TODO: add __dir__ method
class UserExtended():
    def __init__(self, user_id=0):
        if user_id <= 0:
            self.user = User()
        else:
            try:
                self.user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.user = User()

    def __setattr__(self, key, value):
        if key == "user":
            self.__dict__[key] = value
        elif hasattr(self.user, key):
            setattr(self.user, key, value)
            self.user.save()
        else:
            return self.setMeta(key, value)

    def __getattr__(self, key):
        if hasattr(self.user, key):
            return getattr(self.user, key)
        else:
            return self.getMeta(key)

    def __delattr__(self, key):
        if key == "user":
            del self.__dict__[key]
        else:
            self.delMeta(key)

    def hasattr(self, key):
        if hasattr(self.user, key):
            return True
        else:
            try:
                getattr(self, key)
                return True
            except:
                return False

    #TODO: check for meta_type filters
    def setMeta(self, key, value):
        try:
            meta_type = UserMetaType.objects.get(key=key)
        except UserMetaType.DoesNotExist:
            raise AttributeError("such meta key not defined")
        except:
            raise AttributeError("unknown error")

        if meta_type.type == 'number':
            value = int(value)
        elif meta_type.type == 'string':
            value = str(value)
        elif meta_type.type == 'choice':
            try:
                data = json.loads(meta_type.data)
                # # check is list value is contained in list data
                if set(value).issubset(set(data)):
                    # for item in input_data:
                    pass
                else:
                    raise AttributeError('No such choice/choises')
            except ValueError:
                raise ValueError("Should be a valid JSON file")
        elif meta_type.type == 'url':
            val = URLValidator()
            try:
                val(value)
            except ValidationError, error:
                print error

        if meta_type.multiple:
            delattr(self, key)  # delete all meta of this type
            if type(value) == type([]) or type(value) == type(list()):
                for value_one in value:
                    self.addMeta(key, value_one)
            else:
                self.addMeta(key, value)
        else:
            try:
                user_meta = UserMeta.objects.get(user=self.user, meta=meta_type)
            except UserMeta.DoesNotExist:
                user_meta = UserMeta(user=self.user, meta=meta_type)    # new meta
            except:
                raise AttributeError("unknown error")

            user_meta.value = value
            user_meta.save()

    def addMeta(self, key, value):
        try:
            meta_type = UserMetaType.objects.get(key=key)
        except UserMetaType.DoesNotExist:
            raise AttributeError("such meta key not defined")
        except:
            raise AttributeError("unknown error")

        user_meta = UserMeta(user=self.user, meta=meta_type, value=value)
        user_meta.save()

    def getMeta(self, key):
        try:
            meta_type = UserMetaType.objects.get(key=key)
        except UserMetaType.DoesNotExist:
            raise AttributeError("no such meta type")
        except:
            raise AttributeError("unknown error")

        try:
            if not meta_type.multiple:
                try:
                    meta = UserMeta.objects.get(user=self.user, meta=meta_type)
                    return meta.value
                except:
                    return None
            else:
                # return array of values
                result = []
                for meta in UserMeta.objects.filter(user=self.user, meta=meta_type):
                    result.append(meta.value)
                if result == []:
                    return None
                return result

        except UserMeta.DoesNotExist:
            raise AttributeError("No such meta")
        except UserMeta.MultipleObjectsReturned:
            raise AttributeError("multiple objects returned")
        except:
            raise AttributeError("unknown error")

        raise AttributeError()

    def delMeta(self, key):
        try:
            meta_type = UserMetaType.objects.get(key=key)
            try:
                return UserMeta.objects.filter(user=self.user, meta=meta_type).delete()
            except:
                return False
        except:
            return False

    def getAttributes(self):
        userMeta = UserMeta.objects.filter(user=self.user)
        userExtended = UserExtended(self.user.id)
        result = {}
        for meta in userMeta:
            if not meta.meta.key in result:
                value = getattr(userExtended, meta.meta.key)
                try:
                    data = json.loads(meta.meta.data)
                except:
                    data = meta.meta.data
                result[meta.meta.key] = {'value': value, 'type': meta.meta.type, 'data': data}
        return result
